up:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f

test:
	pytest tests/ -v --cov=api --cov-fail-under=75

lint:
	flake8 api/ dashboard/ tests/ || true

dev:
	# lancer l'API et le dashboard localement (non-docker)
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 &
	streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0
# ─── CONFIGURATION ET VARIABLES ──────────────────────────────────────────────
PORT ?= 8000
IMAGE_NAME = devops-monitor-api
CONTAINER_NAME = devops-monitor-app
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

.PHONY: help init run build test test-api stop clean build-images push-acr deploy-azure destroy

# ─── MENU D'AIDE (DEFAULT TARGET) ────────────────────────────────────────────
help:
	@echo "Available commands:"
	@echo "  make init      - Create virtual env & install libraries"
	@echo "  make run       - Run the app locally on port $(PORT)"
	@echo "  make build     - Build the docker image"
	@echo "  make dev       - Run API and Dashboard locally without Docker"
	@echo "  make test      - Run the unit tests"
	@echo "  make test-api  - Run the containerized app"
	@echo "  make stop      - Stop the running container"
	@echo "  make clean     - Remove stopped containers"
	@echo "  make build-images - Build API+Dashboard images for ACR"
	@echo "  make push-acr  - Push images to ACR (requires ACR_NAME)"
	@echo "  make deploy-azure - Deploy or update Azure Container Apps (requires env vars)"
	@echo "  make destroy   - Delete Azure resource group (irreversible)"

# ─── COMMANDES DE DÉVELOPPEMENT LOCAL ────────────────────────────────────────

# Initialisation de l'environnement virtuel et installation des dépendances
init:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install fastapi "uvicorn[standard]" psutil streamlit websockets httpx pandas pytest pytest-cov

# Lancement de l'application (Uvicorn / FastAPI remplace Flask ici)
	@echo "  make destroy   - Delete Azure resource group (irreversible)"
run:
	source $(VENV)/bin/activate && uvicorn api.main:app --reload --port $(PORT)

dev:
	# Run both services in dev mode (separate terminals recommended)
	@echo "Run the API: source $(VENV)/bin/activate && uvicorn api.main:app --reload --port $(PORT)"
	@echo "Run the Dashboard: source $(VENV)/bin/activate && streamlit run dashboard/app.py"

# Exécution des tests unitaires locaux et calcul de la couverture
test:
	source $(VENV)/bin/activate && pytest tests/ -v --cov=api --cov-fail-under=75



# Docker compose helpers (standardized targets)
up:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f


# ─── COMMANDES DOCKER (CONTENEURISATION) ─────────────────────────────────────

# Création de l'image Docker
build:
	docker build -t $(IMAGE_NAME):latest .

# Lancement de l'application conteneurisée (Expose le port configuré)
test-api:
	docker run -d -p $(PORT):$(PORT) --name $(CONTAINER_NAME) $(IMAGE_NAME):latest

# Arrêt du conteneur en cours d'exécution
stop:
	docker stop $(CONTAINER_NAME) || true

# Suppression du conteneur arrêté et nettoyage
clean:
	docker rm $(CONTAINER_NAME) || true

# -------------------- Azure / CI helpers (local) --------------------------
# These targets rely on environment variables set locally (do NOT commit secrets)
# Required env variables: ACR_NAME, AZURE_RESOURCE_GROUP, AZURE_CONTAINERAPPS_ENV, API_KEY
ACR_NAME ?= $(ACR_NAME)
AZURE_RESOURCE_GROUP ?= $(AZURE_RESOURCE_GROUP)
AZURE_CONTAINERAPPS_ENV ?= $(AZURE_CONTAINERAPPS_ENV)
API_APP_NAME ?= devops-monitor-api
DASH_APP_NAME ?= devops-monitor-dashboard

.PHONY: build-images push-acr deploy-azure

.PHONY: destroy

build-images:
	@echo "Building API and Dashboard images (tag: latest)..."
	@if [ -z "$(ACR_NAME)" ]; then echo "ACR_NAME not set. export ACR_NAME=youracrname"; exit 1; fi
	docker build -t $(ACR_NAME).azurecr.io/devops-monitor-api:latest -f api/Dockerfile .
	docker build -t $(ACR_NAME).azurecr.io/devops-monitor-dashboard:latest -f dashboard/Dockerfile .

push-acr:
	@echo "Pushing images to ACR: $(ACR_NAME)"
	@if [ -z "$(ACR_NAME)" ]; then echo "ACR_NAME not set. export ACR_NAME=youracrname"; exit 1; fi
	az acr login --name $(ACR_NAME)
	docker push $(ACR_NAME).azurecr.io/devops-monitor-api:latest
	docker push $(ACR_NAME).azurecr.io/devops-monitor-dashboard:latest

deploy-azure:
	@echo "Deploying Container Apps (will create or update)..."
	@if [ -z "$(ACR_NAME)" ] || [ -z "$(AZURE_RESOURCE_GROUP)" ] || [ -z "$(AZURE_CONTAINERAPPS_ENV)" ] || [ -z "$(API_KEY)" ]; then \
		echo "Please set ACR_NAME, AZURE_RESOURCE_GROUP, AZURE_CONTAINERAPPS_ENV, API_KEY"; exit 1; \
	fi

destroy:
	@echo "Destroying Azure resource group: $(AZURE_RESOURCE_GROUP)"
	@if [ -z "$(AZURE_RESOURCE_GROUP)" ]; then echo "AZURE_RESOURCE_GROUP not set. export AZURE_RESOURCE_GROUP=your-rg"; exit 1; fi
	az group delete --name $(AZURE_RESOURCE_GROUP) --yes --no-wait

# ----------------- Azure Web App for Containers helpers ------------------
.PHONY: webapp-create webapp-deploy webapp-delete

# Variables used by these targets (do not store secrets in repo):
# AZ_WEBAPP_PLAN, AZ_WEBAPP_NAME_API, AZ_WEBAPP_NAME_DASH, ACR_NAME, RESOURCE_GROUP, LOCATION
AZ_WEBAPP_PLAN ?= devops-monitor-plan
AZ_WEBAPP_NAME_API ?= devops-monitor-api-web
AZ_WEBAPP_NAME_DASH ?= devops-monitor-dashboard-web
RESOURCE_GROUP ?= $(AZURE_RESOURCE_GROUP)
LOCATION ?= swedencentral

webapp-create:
	@echo "Creating App Service plan and Web Apps (API + Dashboard)..."
	@if [ -z "$(ACR_NAME)" ] || [ -z "$(RESOURCE_GROUP)" ]; then \
		echo "Please set ACR_NAME and RESOURCE_GROUP (or AZURE_RESOURCE_GROUP)"; exit 1; \
	fi

	# Create App Service plan (Linux, reserved)
	az appservice plan create --name $(AZ_WEBAPP_PLAN) --resource-group $(RESOURCE_GROUP) --is-linux --sku B1 --location $(LOCATION)

	# Create API Web App
	az webapp create --resource-group $(RESOURCE_GROUP) --plan $(AZ_WEBAPP_PLAN) --name $(AZ_WEBAPP_NAME_API) --deployment-container-image-name $(ACR_NAME).azurecr.io/devops-monitor-api:latest

	# Create Dashboard Web App
	az webapp create --resource-group $(RESOURCE_GROUP) --plan $(AZ_WEBAPP_PLAN) --name $(AZ_WEBAPP_NAME_DASH) --deployment-container-image-name $(ACR_NAME).azurecr.io/devops-monitor-dashboard:latest

webapp-deploy:
	@echo "Deploying images to Azure Web Apps (ensure image is pushed to ACR first)"
	@if [ -z "$(ACR_NAME)" ] || [ -z "$(RESOURCE_GROUP)" ]; then \
		echo "Please set ACR_NAME and RESOURCE_GROUP"; exit 1; \
	fi

	# Configure Web Apps to pull from ACR (requires ACR to allow access)
	az webapp config container set --name $(AZ_WEBAPP_NAME_API) --resource-group $(RESOURCE_GROUP) --docker-custom-image-name $(ACR_NAME).azurecr.io/devops-monitor-api:latest
	az webapp config container set --name $(AZ_WEBAPP_NAME_DASH) --resource-group $(RESOURCE_GROUP) --docker-custom-image-name $(ACR_NAME).azurecr.io/devops-monitor-dashboard:latest

webapp-delete:
	@echo "Deleting Web Apps and App Service plan (non-blocking)"
	@if [ -z "$(RESOURCE_GROUP)" ]; then echo "Please set RESOURCE_GROUP"; exit 1; fi
	az webapp delete --name $(AZ_WEBAPP_NAME_API) --resource-group $(RESOURCE_GROUP) || true
	az webapp delete --name $(AZ_WEBAPP_NAME_DASH) --resource-group $(RESOURCE_GROUP) || true
	az appservice plan delete --name $(AZ_WEBAPP_PLAN) --resource-group $(RESOURCE_GROUP) --yes || true
	# API
	@echo "Deploying API: $(API_APP_NAME)"
	@if az containerapp show --name $(API_APP_NAME) --resource-group $(AZURE_RESOURCE_GROUP) >/dev/null 2>&1; then \
		az containerapp update --name $(API_APP_NAME) --resource-group $(AZURE_RESOURCE_GROUP) --image $(ACR_NAME).azurecr.io/devops-monitor-api:latest --set-env-vars API_KEY=$(API_KEY); \
	else \
		az containerapp create --name $(API_APP_NAME) --resource-group $(AZURE_RESOURCE_GROUP) --environment $(AZURE_CONTAINERAPPS_ENV) --image $(ACR_NAME).azurecr.io/devops-monitor-api:latest --target-port 8000 --ingress external --env-vars API_KEY=$(API_KEY); \
	fi

	# Dashboard
	@echo "Deploying Dashboard: $(DASH_APP_NAME)"
	API_BASE_URL=https://$(API_APP_NAME).$(AZURE_CONTAINERAPPS_ENV).azurecontainerapps.io; \
	if az containerapp show --name $(DASH_APP_NAME) --resource-group $(AZURE_RESOURCE_GROUP) >/dev/null 2>&1; then \
		az containerapp update --name $(DASH_APP_NAME) --resource-group $(AZURE_RESOURCE_GROUP) --image $(ACR_NAME).azurecr.io/devops-monitor-dashboard:latest --set-env-vars API_BASE_URL=$$API_BASE_URL; \
	else \
		az containerapp create --name $(DASH_APP_NAME) --resource-group $(AZURE_RESOURCE_GROUP) --environment $(AZURE_CONTAINERAPPS_ENV) --image $(ACR_NAME).azurecr.io/devops-monitor-dashboard:latest --target-port 8501 --ingress external --env-vars API_BASE_URL=$$API_BASE_URL; \
	fi

