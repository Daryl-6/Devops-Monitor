from dataclasses import dataclass, field
from pydantic import BaseModel, Field

@dataclass
class Server:
    """Représentation interne en mémoire d'un serveur surveillé."""
    id: int
    name: str
    host: str
    port: int
    status: str = "unknown"
    tags: list[str] = field(default_factory=list)

    def base_url(self) -> str:
        """Génère l'URL d'accès réseau de la machine."""
        protocol = "https" if self.port == 443 else "http"
        return f"{protocol}://{self.host}:{self.port}"

class ServerIn(BaseModel):
    """Modèle de validation pour l'enregistrement d'un serveur."""
    name: str = Field(..., min_length=1, description="Nom unique de la machine")
    host: str = Field(..., description="Adresse IP ou nom de domaine DNS")
    port: int = Field(default=8080, ge=1, le=65535, description="Port réseau d'écoute")
    tags: list[str] = []

class ServerOut(BaseModel):
    """Modèle de sérialisation pour les réponses renvoyées aux clients."""
    id: int
    name: str
    host: str
    port: int
    status: str
    tags: list[str] = []

    model_config = {"from_attributes": True}
