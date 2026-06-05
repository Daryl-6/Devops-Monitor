 # Devops Monitor — guide en français

Ce dépôt contient une petite API écrite avec FastAPI et un tableau de bord Streamlit qui affiche des métriques système en quasi-temps réel. Il est fourni avec les Dockerfiles et les tests pour faciliter l'exécution locale et le déploiement (ex. Azure Web Apps + ACR).

## Structure du dépôt

- `api/` — application FastAPI exposant des routes HTTP et un WebSocket (`/metrics`, `/health`, `/ws/metrics`).
- `dashboard/` — dashboard Streamlit qui se connecte à l'API via WSS (si HTTPS) ou via polling HTTP en secours.
- `tests/` — tests pytest couvrant les fonctionnalités principales.
- `api/Dockerfile`, `dashboard/Dockerfile` — Dockerfiles pour construire les images.
- `docker-compose.yml` — définition docker-compose pour exécuter localement les deux services.
- `Makefile` — cibles pratiques (test, build, up, down, etc.).
- `.env.example` — exemples de variables d'environnement (ne pas committer vos secrets).

## Liens rapides 

- API publique (exemple) : https://devops-monitor-api-web.azurewebsites.net
- Dashboard public (exemple) : https://devops-monitor-dashboard-web.azurewebsites.net

Remplacez ces URLs par celles de mon déploiement lorsque vous mettez en production.

## Démarrage local

Prérequis

- Python 3.11+ (utiliser un virtualenv recommandé)
- Docker et docker-compose pour exécuter en conteneurs

1) Installer les dépendances

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Lancer les tests

```bash
make test
# ou
pytest -v
```

3) Lancer localement avec docker-compose

```bash
docker-compose up --build
```

Par défaut l'API sera disponible sur `http://localhost:8000` et le dashboard sur `http://localhost:8501`.

## Exécution en Docker (services séparés)

Construire et lancer l'API

```bash
docker build -t devops-monitor-api -f api/Dockerfile api
docker run -p 8000:8000 --env-file .env devops-monitor-api
```

Construire et lancer le dashboard

```bash
docker build -t devops-monitor-dashboard -f dashboard/Dockerfile dashboard
docker run -p 8501:8501 --env-file .env devops-monitor-dashboard
```

## Déploiement 

Pattern recommandé : construire des images Docker, les pousser dans Azure Container Registry (ACR) puis configurer des Azure Web Apps (Linux) pour tirer les images depuis ACR.

Points de sécurité et bonnes pratiques

- Ne stockez jamais de secrets dans le dépôt. Utilisez Azure Key Vault ou les App Settings (Application Settings) du Web App.
- Préférez l'utilisation de Managed Identity + rôle `AcrPull` pour permettre aux Web Apps de récupérer les images depuis ACR sans stocker de credentials.
- Configurez `WEBSITES_PORT` pour correspondre au port exposé par le container (API: 8000, Dashboard: 8501).
- Activez WebSockets sur l'App Service API si vous souhaitez utiliser `wss://`.

CI/CD 

Un pipeline CI/CD typique :

1. Exécuter les tests.
2. Construire les images et les tagger (par SHA ou tag sémantique).
3. Pousser l'image vers ACR (via GitHub OIDC, service principal ou autre mécanisme sécurisé).
4. Mettre à jour la Web App (linuxFxVersion) pour pointer sur la nouvelle image ou utiliser un mécanisme de déploiement continu.

Je peux préparer un workflow GitHub Actions pour automatiser ces étapes, mais je ne le pousserai pas sur `main` sans votre accord.

## Configuration et variables d'environnement

- Copiez `.env.example` en `.env` pour vos tests locaux et remplissez les valeurs. Ne commitez jamais `.env`.
- Le dashboard lit `API_BASE_URL` (ex : `https://<votre-api>.azurewebsites.net`) et tente automatiquement `wss://` si l'URL est en HTTPS.

## Health check et démarrage

- L'API expose `/health` pour les probes de readiness/startup. Configurez la Web App health check sur `/health`.

## Remerciements

Merci pour ce projet : c'était un bon exercice pour démontrer le déploiement de services conteneurisés et un dashboard temps réel. Si vous voulez que je :

- prépare une PR avec ces changements pour revue ;
- écrive le workflow CI/CD complet (build/push/deploy) sur une branche dédiée ;
- améliore la logique de reconnexion WebSocket dans le dashboard ;

dites-moi ce que vous préférez et je m'en occupe.

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
# DevOps Monitoring Dashboard

Projet final — API FastAPI + Dashboard Streamlit, containerisé et déployé sur Azure.

## Description

Un petit système de monitoring écrit en Python. L'API expose des métriques système et un CRUD de serveurs. Le dashboard Streamlit consomme l'API pour afficher des KPIs et un tableau de serveurs.

## Architecture

- Backend : `api/` (FastAPI, uvicorn)
- Frontend : `dashboard/` (Streamlit)
- Tests : `tests/` (pytest)
- Containerisation : Docker + `docker-compose.yml`

## Prérequis

- Python 3.11
- Docker & Docker Compose
- Azure CLI connecté (si vous souhaitez déployer)

## Lancement local

1. Copier le template d'env :

```bash
cp .env.example .env
```

2. Démarrer la stack (Docker) :

```bash
make up
```

3. API : http://localhost:8000
	- Health : http://localhost:8000/health
	- Docs : http://localhost:8000/docs

4. Dashboard (Streamlit) : http://localhost:8501

5. Tests :

```bash
make test
```

## Déploiement sur Azure (actions effectuées)

J'ai construit et poussé les images suivantes dans votre ACR `devopsmonitoracr.azurecr.io` :

- devops-monitor-api:latest
- devops-monitor-dashboard:latest

J'ai configuré les Web Apps existantes pour pointer sur ces images (pull via managed identity). URL publiques :

- API : https://devops-monitor-api-web.azurewebsites.net (Health: /health)
- Dashboard : https://devops-monitor-dashboard-web.azurewebsites.net

Notes opérationnelles :

- Le push des images a été effectué depuis ma session. Les Web Apps sont paramétrées pour utiliser l'identité managée afin d'aller chercher les images dans ACR (AcrPull assigné).
- Le health check de l'API est activé sur `/health`.

## CI/CD

Un workflow minimal `/.github/workflows/ci-cd.yml` est présent et exécute les tests. Si vous souhaitez un pipeline complet (build → push vers ACR → déploiement), je peux préparer le fichier et le laisser en draft avant commit.

## Sécurité

- Ne commitez jamais `.env` ou secrets. Utilisez les Secrets GitHub pour CI.
- L'ACR admin user est désactivé ; les Web Apps utilisent une identité managée avec rôle `AcrPull`.

## Notes & suivi

- Tests unitaires : `pytest tests/` → 6 passed (au moment du run local).
- Prochaine étape proposée : créer un workflow CI/CD complet et/ou ouvrir une branche `exercise/setup` pour revue avant merge.

----cmd à taper sur le terminal 2----
streamlit run dashboard/app.py

----validation et tests
pytest -v && pytest --cov=api tests/
