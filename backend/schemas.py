"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         CONTRATO DE API  —  Olist BI Dashboard · Capítulo 9                ║
║  Todos los endpoints del backend siguen estos schemas Pydantic.             ║
║  Para conectar con la base de datos real (PostgreSQL/Hive via DBeaver)      ║
║  basta con modificar DATABASE_URL en .env y re-ejecutar backend/seed.py.    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


# ─── Filtros comunes ───────────────────────────────────────────────────────────

class FiltrosQuery(BaseModel):
    fecha_inicio: Optional[date] = Field(None, description="Fecha de inicio del período (YYYY-MM-DD)")
    fecha_fin: Optional[date] = Field(None, description="Fecha de fin del período (YYYY-MM-DD)")
    region: Optional[str] = Field(None, description="Región de Brasil: Norte, Nordeste, Centro-Oeste, Sudeste, Sul")
    estado: Optional[str] = Field(None, description="Estado (UF) del cliente: SP, RJ, MG, …")
    categoria: Optional[str] = Field(None, description="Categoría de producto en español")
    metodo_pago: Optional[str] = Field(None, description="Tipo de pago: credit_card, boleto, voucher, debit_card")


# ─── 9.1  Resumen Ejecutivo ────────────────────────────────────────────────────

class KPICard(BaseModel):
    """Tarjeta de KPI individual para el resumen ejecutivo."""
    kpi_id: str = Field(..., description="Identificador: KPI-1 … KPI-10")
    nombre: str
    valor: float
    unidad: str = Field(..., description="BRL, %, días, unidades")
    variacion_pct: float = Field(..., description="% de cambio vs. período anterior")
    tendencia: str = Field(..., description="up | down | stable")


class ClienteTopItem(BaseModel):
    customer_id: str
    ciudad: str
    estado: str
    num_pedidos: int
    ingreso_acumulado_brl: float
    ticket_promedio_brl: float


class ResumenEjecutivoResponse(BaseModel):
    """Respuesta completa del resumen ejecutivo (9.1)."""
    periodo_inicio: date
    periodo_fin: date
    total_pedidos: int
    total_ingresos_brl: float
    kpis: list[KPICard]
    top_clientes: list[ClienteTopItem]


# ─── 9.2  Vistas Acumulativas ─────────────────────────────────────────────────

class PuntoSerie(BaseModel):
    periodo: str = Field(..., description="Etiqueta mes: '2017-01'")
    anio: int
    mes: int
    nombre_mes: str
    valor: float


class SerieAcumulativa(BaseModel):
    nombre: str
    unidad: str
    puntos: list[PuntoSerie]


class IngresosMensualesItem(BaseModel):
    periodo: str
    anio: int
    mes: int
    nombre_mes: str
    region: str
    num_pedidos: int
    ingresos_brl: float
    ticket_promedio_brl: float
    pedidos_cancelados: int
    tasa_cancelacion_pct: float


class VistaAcumulativaResponse(BaseModel):
    """Respuesta para vistas acumulativas (9.2)."""
    ingresos_mensuales: list[IngresosMensualesItem]
    serie_ingresos_acumulados: SerieAcumulativa
    serie_pedidos: SerieAcumulativa
    serie_ticket_promedio: SerieAcumulativa
    serie_margen_pct: SerieAcumulativa


# ─── 9.3  Vista Comparativa ───────────────────────────────────────────────────

class CategoriaItem(BaseModel):
    categoria: str
    grupo: str
    total_items: int
    ingresos_brl: float
    contribucion_brl: float
    margen_pct: float
    participacion_vol_pct: float
    participacion_ing_pct: float
    rank_ingresos: int
    rank_margen: int


class EstadoItem(BaseModel):
    estado: str
    region: str
    num_pedidos: int
    ingresos_brl: float
    ticket_promedio_brl: float
    participacion_pct: float
    tiempo_entrega_prom: float


class MetodoPagoItem(BaseModel):
    metodo: str
    descripcion: str
    num_pedidos: int
    monto_total_brl: float
    ticket_promedio_brl: float
    participacion_frecuencia_pct: float
    participacion_monto_pct: float


class VistaComparativaResponse(BaseModel):
    """Respuesta para vistas comparativas (9.3)."""
    categorias: list[CategoriaItem]
    estados: list[EstadoItem]
    metodos_pago: list[MetodoPagoItem]


# ─── 9.4  KPI Semaforizado ────────────────────────────────────────────────────

class SemaforoKPI(BaseModel):
    """KPI con indicador semáforo (verde/amarillo/rojo)."""
    kpi_id: str
    nombre: str
    valor_actual: float
    unidad: str
    meta_verde: float = Field(..., description="Umbral mínimo para verde (favorable)")
    meta_amarilla: float = Field(..., description="Umbral mínimo para amarillo")
    color: str = Field(..., description="green | yellow | red")
    descripcion_meta: str
    formula: str
    variacion_pct: float
    historico: list[PuntoSerie]


class KPISemafoризadoResponse(BaseModel):
    """Respuesta para KPIs semaforizados (9.4)."""
    semaforos: list[SemaforoKPI]
    resumen_colores: dict = Field(
        ...,
        description="{'green': N, 'yellow': N, 'red': N}"
    )


# ─── 9.5  Filtros y Segmentadores ─────────────────────────────────────────────

class OpcionesFiltros(BaseModel):
    """Opciones disponibles para los filtros del dashboard (9.5)."""
    regiones: list[str]
    estados: list[str]
    categorias: list[str]
    grupos_categoria: list[str]
    metodos_pago: list[str]
    fecha_min: date
    fecha_max: date
    anios: list[int]
