import json
import time
import httpx
import pandas as pd
import streamlit as st
import websockets

API_BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"

st.set_page_config(page_title="DevOps Monitor Dashboard", page_icon="📊", layout="wide")

# ─── CACHED API FETCHERS ──────────────────────────────────────────────────────

@st.cache_data(ttl=5)
def fetch_servers_list() -> list[dict]:
    """Récupère l'inventaire des serveurs depuis l'API (Cache de 5 secondes)."""
    try:
        with httpx.Client(timeout=3.0) as client:
            response = client.get(f"{API_BASE}/servers")
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return []

# ─── SIDEBAR MANAGEMENT ────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Paramètres")
    
    # Gestion du token secret d'écriture
    if "api_key" not in st.session_state:
        st.session_state.api_key = "demo-key"
    
    st.session_state.api_key = st.text_input("Clé d'API (X-API-Key)", value=st.session_state.api_key, type="password")
    st.divider()
    
    st.subheader("➕ Enregistrer un serveur")
    with st.form("add_server_form", clear_on_submit=True):
        srv_name = st.text_input("Nom de la machine", placeholder="api-prod-1")
        srv_host = st.text_input("Hôte DNS / IP", placeholder="httpbin.org")
        srv_port = st.number_input("Port Réseau", min_value=1, max_value=65535, value=443)
        submit_btn = st.form_submit_button("Ajouter à l'inventaire")
        
    if submit_btn:
        if not srv_name or not srv_host:
            st.error("Le nom et l'hôte sont obligatoires.")
        else:
            try:
                headers = {"X-API-Key": st.session_state.api_key}
                payload = {"name": srv_name, "host": srv_host, "port": srv_port}
                with httpx.Client() as client:
                    res = client.post(f"{API_BASE}/servers", json=payload, headers=headers, timeout=5.0)
                if res.status_code == 201:
                    st.success(f"Serveur '{srv_name}' ajouté !")
                    fetch_servers_list.clear() # Invalidation du cache pour forcer l'affichage
                    st.rerun()
                else:
                    st.error(f"Erreur {res.status_code} : {res.text}")
            except Exception as e:
                st.error(f"Impossible de joindre l'API : {e}")

# ─── MAIN APP DASHBOARD ───────────────────────────────────────────────────────

st.title("🖥️ DevOps Server Supervision System")
tab_metrics, tab_servers = st.tabs(["📊 Métriques Temps Réel", "🗄️ Parc de Serveurs"])

# 📌 Onglet 1 — Métriques en Temps Réel via WebSocket direct (Stretch Goal 4)
with tab_metrics:
    st.subheader("Indicateurs de performance de la machine hôte")
    
    # Initialisation de l'historique dans le session state pour le graphique linéaire
    if "metrics_history" not in st.session_state:
        st.session_state.metrics_history = []

    # Conteneurs Streamlit vides pour rafraîchir l'UI dynamiquement sans rechargement de page global
    tiles_placeholder = st.empty()
    chart_placeholder = st.empty()
    
    # Connexion directe par WebSocket (Non-bloquant / Pas de loop st.rerun infini)
    try:
        import asyncio
        async def listen_ws():
            async with websockets.connect(f"{WS_BASE}/ws/metrics") as ws:
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    
                    # Accumulation des 60 derniers points
                    st.session_state.metrics_history.append({
                        "Horodatage": time.strftime("%H:%M:%S"),
                        "CPU %": data["cpu_percent"],
                        "RAM %": data["memory_percent"]
                    })
                    if len(st.session_state.metrics_history) > 60:
                        st.session_state.metrics_history.pop(0)
                        
                    # Rendu dynamique des indicateurs
                    with tiles_placeholder.container():
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Charge CPU", f"{data['cpu_percent']:.1f} %")
                        c2.metric("Mémoire Vive (RAM)", f"{data['memory_percent']:.1f} %", f"{data['memory_used_gb']} / {data['memory_total_gb']} GB")
                        c3.metric("Espace Disque (/)", f"{data['disk_percent']:.1f} %")
                        c4.metric("Canal de Données", "🟢 WebSocket Actif")
                    
                    # Rendu dynamique du graphique
                    with chart_placeholder.container():
                        df = pd.DataFrame(st.session_state.metrics_history)
                        df = df.set_index("Horodatage")
                        st.line_chart(df, height=220)
                    
                    time.sleep(1) # Temporisation locale d'un cycle
                    
        # Lancement sécurisé de la boucle d'écoute
        asyncio.run(listen_ws())
    except Exception:
        st.warning("🔄 Connexion au flux de métriques en cours d'établissement ou l'API est hors-ligne.")
        if st.button("Tenter une reconnexion manuelle"):
            st.rerun()

# 📌 Onglet 2 — Gestion et Affichage du Parc de Serveurs (CRUD & Polling)
with tab_servers:
    st.subheader("État de santé des machines enregistrées")
    servers = fetch_servers_list()
    
    if not servers:
        st.info("Aucun serveur n'est enregistré pour le moment. Utilisez le panneau latéral gauche.")
    else:
        # Transformation en DataFrame pour l'affichage en tableau structuré
        df_servers = pd.DataFrame(servers)
        
        # Formatage visuel selon le statut
        def color_status(val):
            if val == "UP": return "background-color: #d4edda; color: #155724; font-weight: bold;"
            if val == "DEGRADED": return "background-color: #fff3cd; color: #856404; font-weight: bold;"
            return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
            
        styled_df = df_servers[["id", "name", "host", "port", "status"]].style.applymap(color_status, subset=["status"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # Actions de maintenance (Check unitaire & Suppression)
        st.divider()
        col_actions, col_delete = st.columns(2)
        
        with col_actions:
            st.markdown("🔍 **Diagnostic Réseau Immédiat**")
            target_check = st.selectbox("Sélectionner une machine à tester", [s["id"] for s in servers], format_func=lambda x: f"[{x}] {next(s['name'] for s in servers if s['id'] == x)}")
            if st.button("Forcer le Health-Check", type="secondary"):
                try:
                    with httpx.Client() as client:
                        res = client.post(f"{API_BASE}/servers/{target_check}/check", timeout=5.0)
                    if res.status_code == 200:
                        st.success(f"Vérification terminée. Nouveau statut : {res.json()['status']}")
                        fetch_servers_list.clear()
                        st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de l'exécution : {e}")
                    
        with col_delete:
            st.markdown("🗑️ **Zone de Danger**")
            target_del = st.selectbox("Sélectionner une machine à détruire", [s["id"] for s in servers], format_func=lambda x: f"[{x}] {next(s['name'] for s in servers if s['id'] == x)}")
            if st.button("Retirer le serveur du Parc", type="primary"):
                try:
                    headers = {"X-API-Key": st.session_state.api_key}
                    with httpx.Client() as client:
                        res = client.delete(f"{API_BASE}/servers/{target_del}", headers=headers, timeout=5.0)
                    if res.status_code == 204:
                        st.success("Serveur radié avec succès.")
                        fetch_servers_list.clear()
                        st.rerun()
                    else:
                        st.error(f"Refus de l'API ({res.status_code}). Vérifiez votre clé d'authentification.")
                except Exception as e:
                    st.error(f"Erreur d'infrastructure : {e}")
