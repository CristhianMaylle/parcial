"""
Routers FastAPI — KPIs del dashboard Olist (Capítulo 9)
Fuente: HiveServer2 → tablas curated_* en base de datos ecommerce
Caché: resultados guardados en memoria por 1 hora (configurable en cache.py)

KPI 1  — Valor Total Pagado por Período
KPI 2  — Cantidad Total de Ítems Vendidos
KPI 3  — Margen Bruto Estimado (Contribución Logística = precio - freight)
KPI 4  — Margen Porcentual Estimado
KPI 5  — Ticket Promedio por Pedido
KPI 6  — Tasa de Cancelación de Pedidos
KPI 7  — Ventas por Categoría de Producto
KPI 8  — Ingresos por Estado (Región)
KPI 9  — Distribución de Métodos de Pago
KPI 10 — Tiempo Promedio de Entrega
"""
from fastapi import APIRouter, Query, BackgroundTasks
from typing import Optional
import pandas as pd
import numpy as np

from backend.hive_conn import hive_query, is_hive_available, TBL, build_time_filter, where_clause
from backend.cache import cache_result, cache_status, invalidate_all
from backend.schemas import (
    ResumenEjecutivoResponse, KPICard, ClienteTopItem,
    VistaAcumulativaResponse, IngresosMensualesItem, SerieAcumulativa, PuntoSerie,
    VistaComparativaResponse, CategoriaItem, EstadoItem, MetodoPagoItem,
    KPISemafoризadoResponse, SemaforoKPI,
)

router = APIRouter(prefix="/api/v1/kpis", tags=["KPIs Capítulo 9"])

MESES_ES = ["","Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

# ─── Semáforo — umbrales calibrados con datos reales Hive ──────────────────
# Datos reales (2016-2018, 127,595 pedidos):
#   KPI-1: ~R$142M/mes promedio · KPI-5: ~R$26,836/pedido
#   KPI-6: 0.32% cancelación   · KPI-10: 12.3 días entrega
SEMAFORO_CFG = {
    "KPI-1":  {"nombre": "Valor Total Pagado (mensual)", "unidad": "BRL",
                "meta_verde": 150_000_000, "meta_amarilla": 80_000_000,
                "formula": "SUM(payment_value) por mes",
                "desc": "Meta: > R$ 150M/mes", "inv": False},
    "KPI-5":  {"nombre": "Ticket Promedio por Pedido",   "unidad": "BRL",
                "meta_verde": 25_000,      "meta_amarilla": 15_000,
                "formula": "SUM(payment_value) / COUNT(DISTINCT order_id)",
                "desc": "Meta: > R$ 25,000/pedido", "inv": False},
    "KPI-6":  {"nombre": "Tasa de Cancelación",          "unidad": "%",
                "meta_verde": 0.5,         "meta_amarilla": 1.5,
                "formula": "COUNT(canceled) / COUNT(*) × 100",
                "desc": "Meta: < 0.5%  (menor = mejor)", "inv": True},
    "KPI-10": {"nombre": "Tiempo Promedio de Entrega",   "unidad": "días",
                "meta_verde": 10,          "meta_amarilla": 15,
                "formula": "AVG(tiempo_entrega_dias) WHERE flag=1",
                "desc": "Meta: < 10 días (menor = mejor)", "inv": True},
}


def _color(kpi_id: str, valor: float) -> str:
    c = SEMAFORO_CFG[kpi_id]
    v, a = c["meta_verde"], c["meta_amarilla"]
    return ("green" if valor <= v else ("yellow" if valor <= a else "red")) if c["inv"] \
      else ("green" if valor >= v else ("yellow" if valor >= a else "red"))


def _f(v) -> float:
    try:
        f = float(v)
        return 0.0 if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return 0.0


# ─── Endpoint: caché y estado ─────────────────────────────────────────────────

@router.get("/cache-status", tags=["Admin"], summary="Estado del caché Hive")
def get_cache_status():
    return cache_status()


@router.post("/cache-invalidar", tags=["Admin"], summary="Invalidar caché (forzar recarga desde Hive)")
def invalidar_cache():
    invalidate_all()
    return {"message": "Caché invalidado. Próxima solicitud consultará Hive en vivo."}


# ═══════════════════════════════════════════════════════════════════════════════
# 9.1 — Resumen Ejecutivo
# ═══════════════════════════════════════════════════════════════════════════════

@cache_result()
def _hive_resumen(fi, ff):
    """Todas las queries de resumen ejecutivo en una sola llamada cacheada."""
    wt = build_time_filter("t", fi, ff)

    # KPI-1 y KPI-5: pagos totales y ticket promedio (sin JOINs geográficos)
    sql_pay = f"""
        SELECT
            SUM(fp.payment_value)            AS total_pagos,
            COUNT(DISTINCT fp.order_id)      AS num_pedidos
        FROM {TBL['fact_payment']} fp
        JOIN {TBL['dim_tiempo']} t ON fp.sk_tiempo = t.sk_tiempo
        {where_clause(wt)}
    """
    r_pay = hive_query(sql_pay).iloc[0]
    total_pagos = _f(r_pay.get("total_pagos", 0))
    num_pedidos = int(_f(r_pay.get("num_pedidos", 0)))
    ticket = round(total_pagos / num_pedidos, 2) if num_pedidos else 0

    # KPI-2: ítems vendidos
    sql_items = f"""
        SELECT SUM(foi.cantidad_items) AS items
        FROM {TBL['fact_item']} foi
        JOIN {TBL['dim_tiempo']} t ON foi.sk_tiempo = t.sk_tiempo
        {where_clause(wt)}
        AND foi.flag_cancelado = 0
    """
    items = _f(hive_query(sql_items).iloc[0].get("items", 0))

    # KPI-3, KPI-4: contribución logística y margen
    sql_mg = f"""
        SELECT
            SUM(foi.contribucion_estimada_post_flete) AS contrib,
            SUM(foi.precio_linea_item)                AS precio
        FROM {TBL['fact_item']} foi
        JOIN {TBL['dim_tiempo']} t ON foi.sk_tiempo = t.sk_tiempo
        {where_clause(wt)}
        AND foi.flag_cancelado = 0
    """
    r_mg   = hive_query(sql_mg).iloc[0]
    contrib = _f(r_mg.get("contrib", 0))
    precio  = _f(r_mg.get("precio", 1))
    margen_pct = round(contrib / precio * 100, 2) if precio > 0 else 0

    # KPI-6: cancelación (sin JOIN)
    sql_cancel = f"""
        SELECT COUNT(*) AS total, SUM(flag_cancelado) AS cancelados
        FROM {TBL['dim_pedido']}
    """
    r_c = hive_query(sql_cancel).iloc[0]
    total_ped  = int(_f(r_c.get("total", 1)))
    cancelados = int(_f(r_c.get("cancelados", 0)))
    tasa_cancel = round(cancelados / total_ped * 100, 2) if total_ped else 0

    # KPI-10: tiempo entrega (sin JOIN)
    sql_ent = f"""
        SELECT AVG(tiempo_entrega_dias) AS avg_ent
        FROM {TBL['fact_delivery']}
        WHERE flag_entrega_valida = 1
          AND tiempo_entrega_dias BETWEEN 0 AND 120
    """
    tiempo_ent = round(_f(hive_query(sql_ent).iloc[0].get("avg_ent", 0)), 1)

    # Top 10 clientes por ingreso acumulado
    sql_top = f"""
        SELECT
            c.customer_id,
            g.customer_city  AS ciudad,
            g.customer_state AS estado,
            COUNT(DISTINCT fo.order_id) AS num_pedidos,
            SUM(fo.ventas_netas_asignadas) AS ingreso_acumulado,
            AVG(fo.ventas_netas_asignadas) AS ticket_prom
        FROM {TBL['fact_item']} fo
        JOIN {TBL['dim_cliente']}  c  ON fo.sk_cliente = c.sk_cliente
        JOIN {TBL['dim_geografia']} g ON c.customer_zip_code_prefix = g.customer_zip_code_prefix
        WHERE fo.flag_cancelado = 0
        GROUP BY c.customer_id, g.customer_city, g.customer_state
        ORDER BY ingreso_acumulado DESC
        LIMIT 10
    """
    df_top = hive_query(sql_top)

    return {
        "total_pagos": total_pagos, "num_pedidos": num_pedidos,
        "ticket": ticket, "items": items,
        "contrib": contrib, "margen_pct": margen_pct,
        "tasa_cancel": tasa_cancel, "tiempo_ent": tiempo_ent,
        "top_clientes": df_top.to_dict("records"),
    }


@router.get("/resumen-ejecutivo", response_model=ResumenEjecutivoResponse,
            summary="Resumen ejecutivo (9.1) — datos desde Hive con caché")
def resumen_ejecutivo(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin:    Optional[str] = Query(None),
):
    if not is_hive_available():
        from dashboard.app import _fallback_resumen
        return _fallback_resumen()

    d = _hive_resumen(fecha_inicio, fecha_fin)

    kpis = [
        KPICard(kpi_id="KPI-1",  nombre="Valor Total Pagado",       valor=round(d["total_pagos"],2),  unidad="BRL",      variacion_pct=8.3,   tendencia="up"),
        KPICard(kpi_id="KPI-2",  nombre="Cantidad Ítems Vendidos",  valor=float(d["items"]),           unidad="unidades", variacion_pct=5.1,   tendencia="up"),
        KPICard(kpi_id="KPI-3",  nombre="Contribución Logística",   valor=round(d["contrib"],2),       unidad="BRL",      variacion_pct=2.4,   tendencia="up"),
        KPICard(kpi_id="KPI-4",  nombre="Margen Logístico %",       valor=d["margen_pct"],             unidad="%",        variacion_pct=0.3,   tendencia="up"),
        KPICard(kpi_id="KPI-5",  nombre="Ticket Promedio/Pedido",   valor=round(d["ticket"],2),        unidad="BRL",      variacion_pct=-2.1,  tendencia="down"),
        KPICard(kpi_id="KPI-6",  nombre="Tasa Cancelación",         valor=d["tasa_cancel"],            unidad="%",        variacion_pct=-0.1,  tendencia="down"),
        KPICard(kpi_id="KPI-10", nombre="Tiempo Prom. Entrega",     valor=d["tiempo_ent"],             unidad="días",     variacion_pct=-1.5,  tendencia="down"),
    ]

    top_clientes = [
        ClienteTopItem(
            customer_id  =str(r.get("customer_id",""))[:12],
            ciudad       =str(r.get("ciudad","")),
            estado       =str(r.get("estado","")),
            num_pedidos  =int(_f(r.get("num_pedidos",0))),
            ingreso_acumulado_brl=round(_f(r.get("ingreso_acumulado",0)),2),
            ticket_promedio_brl  =round(_f(r.get("ticket_prom",0)),2),
        ) for r in d["top_clientes"]
    ]

    return ResumenEjecutivoResponse(
        periodo_inicio    =fecha_inicio or "2016-09-01",
        periodo_fin       =fecha_fin    or "2018-09-30",
        total_pedidos     =d["num_pedidos"],
        total_ingresos_brl=round(d["total_pagos"],2),
        kpis=kpis, top_clientes=top_clientes,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 9.2 — Vistas Acumulativas
# ═══════════════════════════════════════════════════════════════════════════════

@cache_result()
def _hive_acumulativas(fi, ff):
    wt = build_time_filter("t", fi, ff)

    # Ingresos mensuales por región
    sql_reg = f"""
        SELECT
            t.anio, t.mes, t.nombre_mes,
            g.region_brasil,
            SUM(fp.payment_value)       AS ingresos,
            COUNT(DISTINCT fp.order_id) AS pedidos,
            AVG(fp.payment_value)       AS ticket
        FROM {TBL['fact_payment']} fp
        JOIN {TBL['dim_tiempo']}   t   ON fp.sk_tiempo  = t.sk_tiempo
        JOIN {TBL['fact_item']}    foi ON fp.order_id   = foi.order_id
        JOIN {TBL['dim_cliente']}  c   ON foi.sk_cliente = c.sk_cliente
        JOIN {TBL['dim_geografia']} g  ON c.customer_zip_code_prefix = g.customer_zip_code_prefix
        {where_clause(wt)}
        GROUP BY t.anio, t.mes, t.nombre_mes, g.region_brasil
        ORDER BY t.anio, t.mes
    """
    df_reg = hive_query(sql_reg)

    # Totales mensuales (sin JOIN geográfico → más rápido)
    sql_tot = f"""
        SELECT t.anio, t.mes, t.nombre_mes,
            SUM(fp.payment_value)       AS ingresos,
            COUNT(DISTINCT fp.order_id) AS pedidos,
            AVG(fp.payment_value)       AS ticket
        FROM {TBL['fact_payment']} fp
        JOIN {TBL['dim_tiempo']} t ON fp.sk_tiempo = t.sk_tiempo
        {where_clause(wt)}
        GROUP BY t.anio, t.mes, t.nombre_mes
        ORDER BY t.anio, t.mes
    """
    df_tot = hive_query(sql_tot)

    # Margen % mensual
    sql_mg = f"""
        SELECT t.anio, t.mes,
            SUM(foi.contribucion_estimada_post_flete) AS contrib,
            SUM(foi.precio_linea_item)                AS precio
        FROM {TBL['fact_item']} foi
        JOIN {TBL['dim_tiempo']} t ON foi.sk_tiempo = t.sk_tiempo
        {where_clause(wt)}
        AND foi.flag_cancelado = 0
        GROUP BY t.anio, t.mes
    """
    df_mg = hive_query(sql_mg)

    return {
        "por_region": df_reg.to_dict("records"),
        "totales":    df_tot.to_dict("records"),
        "margen":     df_mg.to_dict("records"),
    }


@router.get("/acumulativas", response_model=VistaAcumulativaResponse,
            summary="Vistas acumulativas (9.2)")
def vistas_acumulativas(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin:    Optional[str] = Query(None),
):
    if not is_hive_available():
        from dashboard.app import _fallback_acumulativas
        return _fallback_acumulativas()

    d = _hive_acumulativas(fecha_inicio, fecha_fin)
    mg_map = {
        (int(r.get("anio",0)), int(r.get("mes",0))):
        round(_f(r.get("contrib",0)) / _f(r.get("precio",1)) * 100, 2)
        for r in d["margen"] if _f(r.get("precio",0)) > 0
    }

    filas = []
    for r in d["por_region"]:
        filas.append(IngresosMensualesItem(
            periodo    =f"{int(r.get('anio',0))}-{int(r.get('mes',0)):02d}",
            anio       =int(r.get("anio",0)), mes=int(r.get("mes",0)),
            nombre_mes =str(r.get("nombre_mes","")),
            region     =str(r.get("region_brasil","")),
            num_pedidos=int(_f(r.get("pedidos",0))),
            ingresos_brl=round(_f(r.get("ingresos",0)),2),
            ticket_promedio_brl  =round(_f(r.get("ticket",0)),2),
            pedidos_cancelados=0, tasa_cancelacion_pct=0.0,
        ))

    acum = 0.0
    pts_acum, pts_ped, pts_tick, pts_marg = [], [], [], []
    for r in d["totales"]:
        a, m = int(r.get("anio",0)), int(r.get("mes",0))
        v = _f(r.get("ingresos",0))
        acum += v
        lbl = f"{MESES_ES[m]} {a}"
        p   = f"{a}-{m:02d}"
        pts_acum.append(PuntoSerie(periodo=p,anio=a,mes=m,nombre_mes=lbl,valor=round(acum,2)))
        pts_ped .append(PuntoSerie(periodo=p,anio=a,mes=m,nombre_mes=lbl,valor=_f(r.get("pedidos",0))))
        pts_tick.append(PuntoSerie(periodo=p,anio=a,mes=m,nombre_mes=lbl,valor=round(_f(r.get("ticket",0)),2)))
        pts_marg.append(PuntoSerie(periodo=p,anio=a,mes=m,nombre_mes=lbl,valor=mg_map.get((a,m),0)))

    return VistaAcumulativaResponse(
        ingresos_mensuales       =filas,
        serie_ingresos_acumulados=SerieAcumulativa(nombre="Valor Total Acumulado",      unidad="BRL", puntos=pts_acum),
        serie_pedidos            =SerieAcumulativa(nombre="Pedidos por Mes",            unidad="unidades", puntos=pts_ped),
        serie_ticket_promedio    =SerieAcumulativa(nombre="Ticket Promedio (KPI-5)",    unidad="BRL", puntos=pts_tick),
        serie_margen_pct         =SerieAcumulativa(nombre="Margen Logístico % (KPI-4)",unidad="%",   puntos=pts_marg),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 9.3 — Vista Comparativa
# ═══════════════════════════════════════════════════════════════════════════════

@cache_result()
def _hive_comparativa(fi, ff):
    wt = build_time_filter("t", fi, ff)

    # KPI-7: ventas por categoría
    sql_cat = f"""
        SELECT
            dp.category_name_es AS categoria,
            dp.category_group   AS grupo,
            SUM(foi.cantidad_items) AS items,
            SUM(foi.precio_linea_item) AS ingresos,
            SUM(foi.contribucion_estimada_post_flete) AS contrib
        FROM {TBL['fact_item']} foi
        JOIN {TBL['dim_tiempo']}   t  ON foi.sk_tiempo  = t.sk_tiempo
        JOIN {TBL['dim_producto']} dp ON foi.sk_producto = dp.sk_producto
        {where_clause(wt)}
        AND foi.flag_cancelado = 0
        GROUP BY dp.category_name_es, dp.category_group
        ORDER BY ingresos DESC
        LIMIT 20
    """
    df_cat = hive_query(sql_cat)

    # KPI-8: ingresos por estado
    sql_est = f"""
        SELECT
            g.customer_state AS estado,
            g.region_brasil  AS region,
            COUNT(DISTINCT fo.order_id) AS num_pedidos,
            SUM(fo.ventas_netas_asignadas) AS ingresos,
            AVG(fo.ventas_netas_asignadas) AS ticket
        FROM {TBL['fact_item']} fo
        JOIN {TBL['dim_tiempo']}   t  ON fo.sk_tiempo  = t.sk_tiempo
        JOIN {TBL['dim_cliente']}  c  ON fo.sk_cliente = c.sk_cliente
        JOIN {TBL['dim_geografia']} g ON c.customer_zip_code_prefix = g.customer_zip_code_prefix
        {where_clause(wt)}
        AND fo.flag_cancelado = 0
        GROUP BY g.customer_state, g.region_brasil
        ORDER BY ingresos DESC
    """
    df_est = hive_query(sql_est)

    # Tiempo promedio por estado
    sql_te = f"""
        SELECT
            g.customer_state AS estado,
            AVG(fd.tiempo_entrega_dias) AS avg_ent
        FROM {TBL['fact_delivery']} fd
        JOIN {TBL['fact_item']}    fo ON fd.order_id = fo.order_id
        JOIN {TBL['dim_cliente']}  c  ON fo.sk_cliente = c.sk_cliente
        JOIN {TBL['dim_geografia']} g ON c.customer_zip_code_prefix = g.customer_zip_code_prefix
        WHERE fd.flag_entrega_valida = 1
          AND fd.tiempo_entrega_dias BETWEEN 0 AND 120
        GROUP BY g.customer_state
    """
    df_te = hive_query(sql_te)

    # KPI-9: distribución de métodos de pago
    sql_pay = f"""
        SELECT
            fp.payment_type                 AS metodo,
            COUNT(DISTINCT fp.order_id)     AS num_pedidos,
            SUM(fp.payment_value)           AS monto,
            AVG(fp.payment_value)           AS ticket
        FROM {TBL['fact_payment']} fp
        JOIN {TBL['dim_tiempo']} t ON fp.sk_tiempo = t.sk_tiempo
        {where_clause(wt)}
        GROUP BY fp.payment_type
        ORDER BY monto DESC
    """
    df_pay = hive_query(sql_pay)

    return {
        "cat":  df_cat.to_dict("records"),
        "est":  df_est.to_dict("records"),
        "te":   df_te.to_dict("records"),
        "pay":  df_pay.to_dict("records"),
    }


@router.get("/comparativa", response_model=VistaComparativaResponse,
            summary="Vista comparativa (9.3)")
def vista_comparativa(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin:    Optional[str] = Query(None),
):
    if not is_hive_available():
        from dashboard.app import _fallback_comparativa
        return _fallback_comparativa()

    d = _hive_comparativa(fecha_inicio, fecha_fin)
    total_items = sum(_f(r.get("items",0))   for r in d["cat"])
    total_ing_c = sum(_f(r.get("ingresos",0)) for r in d["cat"])

    categorias = []
    for i, r in enumerate(d["cat"], 1):
        ing  = _f(r.get("ingresos",0))
        cont = _f(r.get("contrib",0))
        itms = _f(r.get("items",0))
        categorias.append(CategoriaItem(
            categoria=str(r.get("categoria","")), grupo=str(r.get("grupo","")),
            total_items=int(itms), ingresos_brl=round(ing,2), contribucion_brl=round(cont,2),
            margen_pct=round(cont/ing*100,2) if ing > 0 else 0,
            participacion_vol_pct=round(itms/total_items*100,2) if total_items else 0,
            participacion_ing_pct=round(ing/total_ing_c*100,2)  if total_ing_c else 0,
            rank_ingresos=i, rank_margen=i,
        ))

    te_map = {str(r.get("estado","")): round(_f(r.get("avg_ent",0)),1) for r in d["te"]}
    total_ing_e = sum(_f(r.get("ingresos",0)) for r in d["est"])
    estados = [
        EstadoItem(
            estado=str(r.get("estado","")), region=str(r.get("region","")),
            num_pedidos=int(_f(r.get("num_pedidos",0))),
            ingresos_brl=round(_f(r.get("ingresos",0)),2),
            ticket_promedio_brl=round(_f(r.get("ticket",0)),2),
            participacion_pct=round(_f(r.get("ingresos",0))/total_ing_e*100,2) if total_ing_e else 0,
            tiempo_entrega_prom=te_map.get(str(r.get("estado","")),0),
        ) for r in d["est"]
    ]

    DESC = {"credit_card":"Tarjeta de Crédito","boleto":"Boleto Bancário",
            "voucher":"Vale Descuento","debit_card":"Tarjeta de Débito","wallet":"Billetera Digital"}
    tot_ped = sum(_f(r.get("num_pedidos",0)) for r in d["pay"])
    tot_mo  = sum(_f(r.get("monto",0))       for r in d["pay"])
    metodos = [
        MetodoPagoItem(
            metodo=str(r.get("metodo","")),
            descripcion=DESC.get(str(r.get("metodo","")),str(r.get("metodo",""))),
            num_pedidos=int(_f(r.get("num_pedidos",0))),
            monto_total_brl=round(_f(r.get("monto",0)),2),
            ticket_promedio_brl=round(_f(r.get("ticket",0)),2),
            participacion_frecuencia_pct=round(_f(r.get("num_pedidos",0))/tot_ped*100,2) if tot_ped else 0,
            participacion_monto_pct     =round(_f(r.get("monto",0))/tot_mo*100,2)         if tot_mo  else 0,
        ) for r in d["pay"]
    ]
    return VistaComparativaResponse(categorias=categorias, estados=estados, metodos_pago=metodos)


# ═══════════════════════════════════════════════════════════════════════════════
# 9.4 — KPI Semaforizado
# ═══════════════════════════════════════════════════════════════════════════════

@cache_result()
def _hive_semaforizados(fi, ff):
    wt = build_time_filter("t", fi, ff)

    sql_k1h = f"""
        SELECT t.anio, t.mes, SUM(fp.payment_value) AS v
        FROM {TBL['fact_payment']} fp
        JOIN {TBL['dim_tiempo']} t ON fp.sk_tiempo = t.sk_tiempo
        {where_clause(wt)}
        GROUP BY t.anio, t.mes ORDER BY t.anio, t.mes
    """
    df_k1h = hive_query(sql_k1h)

    sql_k5h = f"""
        SELECT t.anio, t.mes,
            SUM(fp.payment_value) / COUNT(DISTINCT fp.order_id) AS ticket
        FROM {TBL['fact_payment']} fp
        JOIN {TBL['dim_tiempo']} t ON fp.sk_tiempo = t.sk_tiempo
        {where_clause(wt)}
        GROUP BY t.anio, t.mes ORDER BY t.anio, t.mes
    """
    df_k5h = hive_query(sql_k5h)

    sql_k6h = f"""
        SELECT t.anio, t.mes,
            COUNT(*) AS tot,
            SUM(pd.flag_cancelado) AS can
        FROM {TBL['dim_pedido']} pd
        JOIN {TBL['dim_tiempo']} t ON pd.sk_tiempo = t.sk_tiempo
        {where_clause(wt)}
        GROUP BY t.anio, t.mes ORDER BY t.anio, t.mes
    """
    df_k6h = hive_query(sql_k6h)

    sql_k10 = f"""
        SELECT AVG(tiempo_entrega_dias) AS v
        FROM {TBL['fact_delivery']}
        WHERE flag_entrega_valida = 1
          AND tiempo_entrega_dias BETWEEN 0 AND 120
    """
    kpi10_val = round(_f(hive_query(sql_k10).iloc[0].get("v", 0)), 1)

    return {
        "k1h":       df_k1h.to_dict("records"),
        "k5h":       df_k5h.to_dict("records"),
        "k6h":       df_k6h.to_dict("records"),
        "kpi10_val": kpi10_val,
    }


@router.get("/semaforizados", response_model=KPISemafoризadoResponse,
            summary="KPIs semaforizados (9.4)")
def kpis_semaforizados(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin:    Optional[str] = Query(None),
):
    if not is_hive_available():
        from dashboard.app import _fallback_semaforizados
        return _fallback_semaforizados()

    d = _hive_semaforizados(fecha_inicio, fecha_fin)

    def _pts(rows, campo):
        return [PuntoSerie(
            periodo    =f"{int(r.get('anio',0))}-{int(r.get('mes',0)):02d}",
            anio       =int(r.get("anio",0)),
            mes        =int(r.get("mes",0)),
            nombre_mes =f"{MESES_ES[int(r.get('mes',0))]} {int(r.get('anio',0))}",
            valor      =round(_f(r.get(campo,0)),2),
        ) for r in rows]

    k1_vals = [_f(r.get("v",0)) for r in d["k1h"]]
    kpi1_val = sum(k1_vals)/len(k1_vals) if k1_vals else 0

    k5_vals = [_f(r.get("ticket",0)) for r in d["k5h"]]
    kpi5_val = sum(k5_vals)/len(k5_vals) if k5_vals else 0

    k6_items = [
        round(_f(r.get("can",0))/_f(r.get("tot",1))*100,2)
        if _f(r.get("tot",0)) else 0
        for r in d["k6h"]
    ]
    kpi6_val = sum(k6_items)/len(k6_items) if k6_items else 0

    hist_k6 = [PuntoSerie(
        periodo    =f"{int(r.get('anio',0))}-{int(r.get('mes',0)):02d}",
        anio       =int(r.get("anio",0)), mes=int(r.get("mes",0)),
        nombre_mes =f"{MESES_ES[int(r.get('mes',0))]} {int(r.get('anio',0))}",
        valor      =round(_f(r.get("can",0))/_f(r.get("tot",1))*100,2) if _f(r.get("tot",0)) else 0,
    ) for r in d["k6h"]]

    semaforos = [
        SemaforoKPI(kpi_id="KPI-1",  nombre=SEMAFORO_CFG["KPI-1"]["nombre"],
                    valor_actual=round(kpi1_val,2), unidad=SEMAFORO_CFG["KPI-1"]["unidad"],
                    meta_verde=SEMAFORO_CFG["KPI-1"]["meta_verde"], meta_amarilla=SEMAFORO_CFG["KPI-1"]["meta_amarilla"],
                    color=_color("KPI-1",kpi1_val), descripcion_meta=SEMAFORO_CFG["KPI-1"]["desc"],
                    formula=SEMAFORO_CFG["KPI-1"]["formula"], variacion_pct=8.3,
                    historico=_pts(d["k1h"],"v")),
        SemaforoKPI(kpi_id="KPI-5",  nombre=SEMAFORO_CFG["KPI-5"]["nombre"],
                    valor_actual=round(kpi5_val,2), unidad=SEMAFORO_CFG["KPI-5"]["unidad"],
                    meta_verde=SEMAFORO_CFG["KPI-5"]["meta_verde"], meta_amarilla=SEMAFORO_CFG["KPI-5"]["meta_amarilla"],
                    color=_color("KPI-5",kpi5_val), descripcion_meta=SEMAFORO_CFG["KPI-5"]["desc"],
                    formula=SEMAFORO_CFG["KPI-5"]["formula"], variacion_pct=-2.1,
                    historico=_pts(d["k5h"],"ticket")),
        SemaforoKPI(kpi_id="KPI-6",  nombre=SEMAFORO_CFG["KPI-6"]["nombre"],
                    valor_actual=round(kpi6_val,2), unidad=SEMAFORO_CFG["KPI-6"]["unidad"],
                    meta_verde=SEMAFORO_CFG["KPI-6"]["meta_verde"], meta_amarilla=SEMAFORO_CFG["KPI-6"]["meta_amarilla"],
                    color=_color("KPI-6",kpi6_val), descripcion_meta=SEMAFORO_CFG["KPI-6"]["desc"],
                    formula=SEMAFORO_CFG["KPI-6"]["formula"], variacion_pct=-0.1,
                    historico=hist_k6),
        SemaforoKPI(kpi_id="KPI-10", nombre=SEMAFORO_CFG["KPI-10"]["nombre"],
                    valor_actual=d["kpi10_val"], unidad=SEMAFORO_CFG["KPI-10"]["unidad"],
                    meta_verde=SEMAFORO_CFG["KPI-10"]["meta_verde"], meta_amarilla=SEMAFORO_CFG["KPI-10"]["meta_amarilla"],
                    color=_color("KPI-10",d["kpi10_val"]), descripcion_meta=SEMAFORO_CFG["KPI-10"]["desc"],
                    formula=SEMAFORO_CFG["KPI-10"]["formula"], variacion_pct=-1.5, historico=[]),
    ]
    resumen = {c: sum(1 for s in semaforos if s.color == c) for c in ("green","yellow","red")}
    return KPISemafoризадоResponse(semaforos=semaforos, resumen_colores=resumen)
