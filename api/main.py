import asyncio
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect

from api.models import Server, ServerIn, ServerOut
from api.auth import verify_api_key
from api.metrics import get_system_metrics
from api.poller import run_poll_loop, poll_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Base de données en mémoire
_store: dict[int, Server] = {}
_counter = 0
poller_task: asyncio.Task | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie (Lifespan) de l'application FastAPI."""
    global poller_task
    # Démarrage du poller en arrière-plan
    poller_task = asyncio.create_task(run_poll_loop(_store, interval=10))
    yield
    # Extinction propre du poller au shutdown
    if poller_task:
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass

app = FastAPI(title="DevOps Monitoring API", version="1.0", lifespan=lifespan)

# ─── ROUTES DU SYSTÈME ────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok"}

@app.get("/metrics", tags=["System"])
async def metrics():
    return get_system_metrics()

@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """Stream de métriques au format JSON en temps réel via WebSocket."""
    await websocket.accept()
    logger.info("Client connecté au flux WebSocket /ws/metrics")
    try:
        while True:
            payload = get_system_metrics()
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("Client déconnecté du flux WebSocket (Fermeture de l'onglet)")

# ─── CRUD SERVEURS ────────────────────────────────────────────────────────────

@app.post("/servers", response_model=ServerOut, status_code=201, tags=["Servers Management"])
async def register_server(server: ServerIn, _: str = Depends(verify_api_key)):
    global _counter
    _counter += 1
    record = Server(
        id=_counter,
        name=server.name,
        host=server.host,
        port=server.port,
        tags=server.tags,
        status="unknown"
    )
    _store[_counter] = record
    return record

@app.get("/servers", response_model=list[ServerOut], tags=["Servers Management"])
async def list_servers(status: str | None = None):
    servers_list = list(_store.values())
    if status:
        servers_list = [s for s in servers_list if s.status.upper() == status.upper()]
    return servers_list

@app.get("/servers/{server_id}", response_model=ServerOut, tags=["Servers Management"])
async def get_server(server_id: int):
    if server_id not in _store:
        raise HTTPException(status_code=404, detail="Serveur introuvable.")
    return _store[server_id]

@app.delete("/servers/{server_id}", status_code=204, tags=["Servers Management"])
async def delete_server(server_id: int, _: str = Depends(verify_api_key)):
    if server_id not in _store:
        raise HTTPException(status_code=404, detail="Serveur introuvable.")
    del _store[server_id]

@app.post("/servers/{server_id}/check", response_model=ServerOut, tags=["Servers Management"])
async def trigger_immediate_check(server_id: int):
    if server_id not in _store:
        raise HTTPException(status_code=404, detail="Serveur introuvable.")
    server = _store[server_id]
    # Forçage immédiat de la vérification sans attendre le poller
    await poll_server(server.id, server.base_url(), _store)
    return server
