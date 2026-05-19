"""Cliente HTTP para el backend FastAPI. Si el backend no responde, usa datos simulados de fallback."""
import os, requests
from datetime import date
from typing import Optional

API_URL = os.getenv("API_URL", "http://localhost:8000")
TIMEOUT = 10


def _get(path: str, params: dict = None) -> dict | None:
    try:
        r = requests.get(f"{API_URL}{path}", params=params or {}, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _build_params(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str]    = None,
    region: Optional[str]       = None,
    estado: Optional[str]       = None,
    categoria: Optional[str]    = None,
    metodo_pago: Optional[str]  = None,
) -> dict:
    p = {}
    if fecha_inicio: p["fecha_inicio"] = fecha_inicio
    if fecha_fin:    p["fecha_fin"]    = fecha_fin
    if region:       p["region"]       = region
    if estado:       p["estado"]       = estado
    if categoria:    p["categoria"]    = categoria
    if metodo_pago:  p["metodo_pago"]  = metodo_pago
    return p


def get_resumen_ejecutivo(**kwargs) -> dict | None:
    return _get("/api/v1/kpis/resumen-ejecutivo", _build_params(**kwargs))


def get_acumulativas(**kwargs) -> dict | None:
    return _get("/api/v1/kpis/acumulativas", _build_params(**kwargs))


def get_comparativa(**kwargs) -> dict | None:
    return _get("/api/v1/kpis/comparativa", _build_params(**kwargs))


def get_semaforizados(**kwargs) -> dict | None:
    return _get("/api/v1/kpis/semaforizados", _build_params(**kwargs))


def get_filtros_opciones() -> dict | None:
    return _get("/api/v1/filtros/opciones")


def check_api_health() -> bool:
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False
