import os
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

# Récupération de la clé depuis l'environnement ou valeur par défaut sécurisée
API_KEY = os.getenv("API_KEY", "demo-key")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(key: str = Security(api_key_header)):
    """Dépendance permettant de sécuriser les accès en écriture de l'API."""
    if not key or key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé API invalide ou absente (Header X-API-Key requis)."
        )
    return key
