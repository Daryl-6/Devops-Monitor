# Mon projet structuré
```text
devops-monitor/
├── api/
│   ├── __init__.py
│   ├── auth.py          # En-tête X-API-Key
│   ├── main.py          # FastAPI, Lifespan & WebSocket
│   ├── metrics.py       # Collecte psutil (CPU, RAM, Disk)
│   ├── models.py        # Pydantic & Dataclass Server
│   └── poller.py        # Poller asynchrone concurrent
├── dashboard/
│   └── app.py           # Interface Streamlit (WebSocket)
├── tests/
│   ├── test_metrics.py  # Tests collecteur
│   └── test_routes.py   # Tests API (TestClient)
└── requirements.txt     # Dépendances
 les cmd 
---Activation de l'ENV virtuel et les dépendances
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi "uvicorn[standard]" psutil streamlit websockets httpx pandas pytest pytest-cov
----cmd à taper sur le terminal 1 -----
uvicorn api.main:app --reload --port 8000

----cmd à taper sur le terminal 2----
streamlit run dashboard/app.py

----validation et tests
pytest -v && pytest --cov=api tests/
