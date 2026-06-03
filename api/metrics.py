import psutil

def get_system_metrics() -> dict:
    """
    Récupère un snapshot des métriques système de la machine locale.
    Utilise la forme non-bloquante de cpu_percent pour préserver l'event loop.
    """
    mem = psutil.virtual_memory()
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": mem.percent,
        "memory_used_gb": round(mem.used / 1e9, 2),
        "memory_total_gb": round(mem.total / 1e9, 2),
        "disk_percent": psutil.disk_usage("/").percent
    }
