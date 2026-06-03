# tests/test_metrics.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../api')))

from metrics import get_system_metrics

def test_get_system_metrics_structure():
    """Vérifie la présence obligatoire des clés de performance système requis."""
    metrics = get_system_metrics()
    assert "cpu_percent" in metrics
    assert "memory_percent" in metrics
    assert "disk_percent" in metrics
    assert "memory_used_gb" in metrics

def test_get_system_metrics_boundaries():
    """Valide que les taux remontés par psutil s'inscrivent dans une échelle de 0 à 100 %."""
    metrics = get_system_metrics()
    assert 0 <= metrics["cpu_percent"] <= 100
    assert 0 <= metrics["memory_percent"] <= 100
    assert 0 <= metrics["disk_percent"] <= 100
