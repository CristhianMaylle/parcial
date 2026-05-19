"""
Caché en memoria con TTL para resultados de Hive.
Primera consulta: lenta (Hive ~30-60s por query).
Subsiguientes:    instantáneas (desde memoria).
"""
import time, hashlib, json, logging
from typing import Any, Optional, Callable
from functools import wraps

log = logging.getLogger("hive_cache")

_CACHE: dict[str, tuple[float, Any]] = {}
DEFAULT_TTL = int(3600)   # 1 hora en segundos


def _key(*args, **kwargs) -> str:
    payload = json.dumps({"a": args, "k": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(payload.encode()).hexdigest()


def get(cache_key: str) -> Optional[Any]:
    entry = _CACHE.get(cache_key)
    if entry:
        ts, val = entry
        if time.time() - ts < DEFAULT_TTL:
            return val
        del _CACHE[cache_key]
    return None


def set(cache_key: str, value: Any) -> None:
    _CACHE[cache_key] = (time.time(), value)


def invalidate_all() -> None:
    _CACHE.clear()
    log.info("Caché invalidado")


def cache_result(ttl: int = DEFAULT_TTL):
    """Decorador: cachea el resultado de una función por TTL segundos."""
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            k = _key(fn.__name__, *args, **kwargs)
            cached = get(k)
            if cached is not None:
                log.debug(f"Cache HIT: {fn.__name__}")
                return cached
            log.info(f"Cache MISS: {fn.__name__} — consultando Hive…")
            result = fn(*args, **kwargs)
            set(k, result)
            return result
        return wrapper
    return decorator


def cache_status() -> dict:
    now = time.time()
    return {
        "entries": len(_CACHE),
        "keys": [
            {"key": k[:8], "age_sec": round(now - v[0]), "expired": (now - v[0]) > DEFAULT_TTL}
            for k, v in _CACHE.items()
        ],
        "ttl_seconds": DEFAULT_TTL,
    }
