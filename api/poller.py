import asyncio
import logging
import httpx
try:
    from api.models import Server
except ModuleNotFoundError:
    from models import Server

logger = logging.getLogger(__name__)

async def poll_server(server_id: int, url: str, store: dict):
    """Effectue un appel HTTP asynchrone pour qualifier le statut du serveur distant."""
    # Simulation/Mock pour httpbin pour éviter les erreurs 404 lors des démos du TP
    target_url = f"{url}/status/200" if "httpbin.org" in url else f"{url}/health"
    
    async with httpx.AsyncClient(timeout=4.0) as client:
        try:
            response = await client.get(target_url)
            if response.status_code == 200:
                store[server_id].status = "UP"
            else:
                store[server_id].status = "DEGRADED"
        except (httpx.ConnectError, httpx.TimeoutException):
            store[server_id].status = "DOWN"
        except Exception as e:
            logger.error(f"Erreur lors du polling du serveur {server_id}: {e}")
            store[server_id].status = "DOWN"

async def run_poll_loop(store: dict, interval: int = 10):
    """Boucle infinie exécutée en tâche de fond pour superviser le parc de machines."""
    logger.info("Démarrage de la boucle de supervision asynchrone (Poller).")
    try:
        while True:
            if store:
                tasks = [
                    poll_server(srv.id, srv.base_url(), store)
                    for srv in list(store.values())
                ]
                await asyncio.gather(*tasks)
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("Arrêt propre de la boucle de supervision (Poller annulé).")
