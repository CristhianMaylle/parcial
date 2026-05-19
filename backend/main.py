import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import kpis, filtros
from backend.hive_conn import is_hive_available, HIVE_HOST, HIVE_PORT, HIVE_DB

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Olist BI API — Capítulo 9",
    description="""
**Dashboard ejecutivo Olist** · SI807U

Fuente de datos: **HiveServer2** sobre Docker
- Host: `sandbox-hdp.hortonworks.com` / puerto `10000`
- Base de datos: `ecommerce` (tablas `curated_*`)
- Si Hive no está disponible, los endpoints devuelven datos simulados.

### KPIs implementados
| ID | Nombre |
|----|--------|
| KPI-1 | Valor Total Pagado por Período |
| KPI-2 | Cantidad Total de Ítems Vendidos |
| KPI-3 | Margen Bruto Estimado (Contribución Logística) |
| KPI-4 | Margen Porcentual Estimado |
| KPI-5 | Ticket Promedio por Pedido |
| KPI-6 | Tasa de Cancelación de Pedidos |
| KPI-7 | Ventas por Categoría de Producto |
| KPI-8 | Ingresos por Estado (Región) |
| KPI-9 | Distribución de Métodos de Pago |
| KPI-10 | Tiempo Promedio de Entrega |
""",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kpis.router)
app.include_router(filtros.router)


@app.get("/", tags=["Health"])
def root():
    hive_ok = is_hive_available()
    return {
        "status": "ok",
        "version": "2.0.0",
        "hive_available": hive_ok,
        "hive_host": f"{HIVE_HOST}:{HIVE_PORT}/{HIVE_DB}",
        "data_source": "Hive (curated_*)" if hive_ok else "Datos simulados (fallback)",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    hive_ok = is_hive_available()
    return {
        "status": "healthy",
        "hive": "connected" if hive_ok else "unavailable (using fallback)",
    }


if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run("backend.main:app", host="0.0.0.0",
                port=int(os.getenv("API_PORT", 8000)), reload=True)
