"""
Conector unificado para HiveServer2 (Docker local).
Intenta pyhive → impyla → fallback PostgreSQL → fallback datos mock.

Conexión Hive:
  Host:     localhost (o sandbox-hdp.hortonworks.com)
  Puerto:   10000
  DB:       ecommerce
  Usuario:  hive / Contraseña: hive
  Protocolo: Thrift / HiveServer2
"""
import os, logging
from typing import Optional
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("hive_conn")

# ── Configuración Hive ──────────────────────────────────────────────────────
HIVE_HOST = os.getenv("HIVE_HOST", "localhost")
HIVE_PORT = int(os.getenv("HIVE_PORT", 10000))
HIVE_DB   = os.getenv("HIVE_DATABASE", "ecommerce")
HIVE_USER = os.getenv("HIVE_USER", "hive")
HIVE_PASS = os.getenv("HIVE_PASSWORD", "hive")

# Prefijo de tablas curated en Hive
TBL = {
    "fact_item":     "curated_fact_orderitem",
    "fact_payment":  "curated_fact_payment",
    "fact_delivery": "curated_fact_delivery",
    "dim_producto":  "curated_dim_producto",
    "dim_pedido":    "curated_dim_pedido",
    "dim_cliente":   "curated_dim_cliente",
    "dim_geografia": "curated_dim_geografia",
    "dim_tiempo":    "curated_dim_tiempo",
    "dim_tipo_pago": "curated_dim_tipo_pago",
}

_DRIVER: Optional[str] = None


def _detect_driver() -> str:
    global _DRIVER
    if _DRIVER:
        return _DRIVER
    try:
        from pyhive import hive  # noqa
        _DRIVER = "pyhive"
        log.info("Driver seleccionado: pyhive")
    except ImportError:
        try:
            from impala.dbapi import connect  # noqa
            _DRIVER = "impyla"
            log.info("Driver seleccionado: impyla")
        except ImportError:
            _DRIVER = "none"
            log.warning("Sin driver Hive — usando fallback")
    return _DRIVER


def _conn_pyhive():
    from pyhive import hive
    # Intentar auth NONE primero (Docker sin Kerberos), luego CUSTOM
    for auth in ("NONE", "CUSTOM"):
        try:
            kw = dict(host=HIVE_HOST, port=HIVE_PORT,
                      database=HIVE_DB, username=HIVE_USER,
                      auth=auth)
            if auth == "CUSTOM":
                kw["password"] = HIVE_PASS
            conn = hive.Connection(**kw)
            conn.cursor().execute("SELECT 1")
            return conn
        except Exception as e:
            log.debug(f"pyhive auth={auth} falló: {e}")
    raise ConnectionError("pyhive: no se pudo conectar con ningún método de auth")


def _conn_impyla():
    from impala.dbapi import connect
    for auth in ("PLAIN", "NOSASL"):
        try:
            conn = connect(
                host=HIVE_HOST, port=HIVE_PORT,
                database=HIVE_DB,
                user=HIVE_USER, password=HIVE_PASS,
                auth_mechanism=auth,
                use_ssl=False,
            )
            conn.cursor().execute("SELECT 1")
            return conn
        except Exception as e:
            log.debug(f"impyla auth={auth} falló: {e}")
    raise ConnectionError("impyla: no se pudo conectar")


def get_hive_connection():
    """Devuelve una conexión activa a HiveServer2."""
    driver = _detect_driver()
    if driver == "pyhive":
        return _conn_pyhive()
    if driver == "impyla":
        return _conn_impyla()
    raise ConnectionError("No hay driver Hive disponible")


def hive_query(sql: str) -> pd.DataFrame:
    """
    Ejecuta una consulta HiveQL y retorna un DataFrame de pandas.
    Usa cursor nativo (evita warning de SQLAlchemy de pandas).
    """
    conn = get_hive_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows    = cursor.fetchall()
        columns = [desc[0].split(".")[-1] for desc in cursor.description] if cursor.description else []
        return pd.DataFrame(rows, columns=columns)
    finally:
        conn.close()


class HiveUnavailableError(Exception):
    pass


def is_hive_available() -> bool:
    try:
        hive_query("SELECT 1")
        return True
    except Exception:
        return False


# ── Helpers de filtro para construir WHERE ────────────────────────────────────

def _safe(val: str) -> str:
    """Escapa comillas simples para prevenir inyección en strings Hive."""
    return str(val).replace("'", "''")


def build_time_filter(alias: str, fi: Optional[str], ff: Optional[str]) -> str:
    parts = []
    if fi:
        parts.append(f"{alias}.fecha >= '{_safe(fi)}'")
    if ff:
        parts.append(f"{alias}.fecha <= '{_safe(ff)}'")
    return " AND ".join(parts)


def build_region_filter(alias: str, region: Optional[str]) -> str:
    if region:
        return f"{alias}.region_brasil = '{_safe(region)}'"
    return ""


def build_state_filter(alias: str, estado: Optional[str]) -> str:
    if estado:
        return f"{alias}.customer_state = '{_safe(estado)}'"
    return ""


def build_category_filter(alias: str, categoria: Optional[str]) -> str:
    if categoria:
        return f"{alias}.category_name_es = '{_safe(categoria)}'"
    return ""


def where_clause(*conditions) -> str:
    active = [c for c in conditions if c]
    return ("WHERE " + " AND ".join(active)) if active else ""
