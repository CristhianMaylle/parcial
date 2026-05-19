"""Fábrica de figuras Plotly con tema futurista para el dashboard Olist."""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional

# ─── Paleta y template base ───────────────────────────────────────────────────

CYAN   = "#00f5ff"
PURPLE = "#8b5cf6"
PINK   = "#f43f5e"
GREEN  = "#10b981"
AMBER  = "#f59e0b"
RED    = "#ef4444"
BLUE   = "#3b82f6"

PALETTE = [CYAN, PURPLE, PINK, GREEN, AMBER, BLUE, "#06b6d4", "#a78bfa",
           "#fb7185", "#34d399", "#fbbf24", "#60a5fa"]

BG      = "#04080f"
BG_CARD = "#080f1e"
GRID    = "rgba(0,245,255,0.07)"
TEXT    = "#94a3b8"
TEXT_H  = "#e2e8f0"

BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(0,0,0,0)",
    font         = dict(family="Inter, Segoe UI, sans-serif", color=TEXT, size=12),
    margin       = dict(l=10, r=10, t=36, b=10),
    legend       = dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT, size=11)),
    colorway     = PALETTE,
)

AXIS_BASE = dict(
    gridcolor=GRID,
    linecolor="rgba(0,245,255,0.15)",
    tickcolor="rgba(0,245,255,0.15)",
    tickfont=dict(color=TEXT, size=10),
    title_font=dict(color=TEXT, size=11),
    showgrid=True,
    zeroline=False,
)


def _base(title: str = "") -> go.Figure:
    fig = go.Figure()
    layout = dict(**BASE_LAYOUT, title=dict(text=title, font=dict(color=TEXT_H, size=13), x=0.01))
    fig.update_layout(**layout)
    return fig


# ─── 9.2 Vistas Acumulativas ─────────────────────────────────────────────────

def fig_ingresos_area(data: dict) -> go.Figure:
    """Área de ingresos mensuales por región."""
    rows = data.get("ingresos_mensuales", [])
    if not rows:
        return _base("Sin datos")
    df = pd.DataFrame(rows)
    fig = _base()
    for region in df["region"].unique():
        sub = df[df["region"] == region].sort_values(["anio", "mes"])
        fig.add_trace(go.Scatter(
            x=sub["periodo"], y=sub["ingresos_brl"],
            name=region, mode="lines",
            fill="tonexty" if region != df["region"].unique()[0] else "tozeroy",
            line=dict(width=2),
            hovertemplate="<b>%{x}</b><br>R$ %{y:,.0f}<extra>" + region + "</extra>",
        ))
    fig.update_layout(
        xaxis=dict(**AXIS_BASE, title="Período"),
        yaxis=dict(**AXIS_BASE, title="Ingresos (BRL)", tickprefix="R$ ", tickformat=",.0f"),
        title=dict(text="Ingresos por Región y Mes", font=dict(color=TEXT_H, size=13), x=0.01),
        hovermode="x unified",
    )
    return fig


def fig_acumulado_line(data: dict) -> go.Figure:
    """Línea de ingresos acumulados en el tiempo."""
    pts = data.get("serie_ingresos_acumulados", {}).get("puntos", [])
    if not pts:
        return _base("Sin datos")
    x = [p["periodo"] for p in pts]
    y = [p["valor"] for p in pts]
    fig = _base()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines+markers",
        line=dict(color=CYAN, width=2.5),
        marker=dict(color=CYAN, size=5),
        fill="tozeroy",
        fillcolor="rgba(0,245,255,0.06)",
        name="Acumulado",
        hovertemplate="<b>%{x}</b><br>R$ %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        xaxis=dict(**AXIS_BASE, title="Período"),
        yaxis=dict(**AXIS_BASE, title="Ingresos Acumulados (BRL)", tickprefix="R$ ", tickformat=",.0f"),
        title=dict(text="Ingresos Acumulados", font=dict(color=TEXT_H, size=13), x=0.01),
    )
    return fig


def fig_pedidos_bar(data: dict) -> go.Figure:
    """Barras de pedidos por mes."""
    pts = data.get("serie_pedidos", {}).get("puntos", [])
    if not pts:
        return _base("Sin datos")
    fig = _base()
    fig.add_trace(go.Bar(
        x=[p["periodo"] for p in pts],
        y=[p["valor"]   for p in pts],
        marker=dict(
            color=[p["valor"] for p in pts],
            colorscale=[[0, "rgba(139,92,246,0.4)"], [1, CYAN]],
            line=dict(color="rgba(0,245,255,0.3)", width=0.5),
        ),
        name="Pedidos",
        hovertemplate="<b>%{x}</b><br>%{y:,.0f} pedidos<extra></extra>",
    ))
    fig.update_layout(
        xaxis=dict(**AXIS_BASE, title="Período"),
        yaxis=dict(**AXIS_BASE, title="Nº Pedidos"),
        title=dict(text="Pedidos por Mes", font=dict(color=TEXT_H, size=13), x=0.01),
        bargap=0.25,
    )
    return fig


def fig_margen_line(data: dict) -> go.Figure:
    """Línea de margen porcentual mensual."""
    pts = data.get("serie_margen_pct", {}).get("puntos", [])
    if not pts:
        return _base("Sin datos")
    fig = _base()
    vals = [p["valor"] for p in pts]
    fig.add_trace(go.Scatter(
        x=[p["periodo"] for p in pts], y=vals,
        mode="lines+markers",
        line=dict(color=PURPLE, width=2.5),
        marker=dict(
            color=[GREEN if v >= 25 else AMBER if v >= 15 else RED for v in vals],
            size=7, line=dict(color="rgba(255,255,255,0.2)", width=1),
        ),
        name="Margen %",
        hovertemplate="<b>%{x}</b><br>%{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=25, line=dict(color=GREEN, width=1, dash="dot"),
                  annotation_text="Meta 25%", annotation_font_color=GREEN)
    fig.update_layout(
        xaxis=dict(**AXIS_BASE, title="Período"),
        yaxis=dict(**AXIS_BASE, title="Margen %", ticksuffix="%"),
        title=dict(text="Margen % Mensual (KPI-6)", font=dict(color=TEXT_H, size=13), x=0.01),
    )
    return fig


def fig_ticket_line(data: dict) -> go.Figure:
    """Ticket promedio mensual."""
    pts = data.get("serie_ticket_promedio", {}).get("puntos", [])
    if not pts:
        return _base("Sin datos")
    vals = [p["valor"] for p in pts]
    fig = _base()
    fig.add_trace(go.Scatter(
        x=[p["periodo"] for p in pts], y=vals,
        mode="lines+markers",
        line=dict(color=AMBER, width=2.5),
        marker=dict(color=AMBER, size=6),
        name="Ticket",
        hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>",
    ))
    fig.add_hline(y=160, line=dict(color=GREEN, width=1, dash="dot"),
                  annotation_text="Meta R$300", annotation_font_color=GREEN)
    fig.add_hline(y=120, line=dict(color=AMBER, width=1, dash="dot"),
                  annotation_text="Umbral R$200", annotation_font_color=AMBER)
    fig.update_layout(
        xaxis=dict(**AXIS_BASE),
        yaxis=dict(**AXIS_BASE, title="Ticket Promedio (BRL)", tickprefix="R$ "),
        title=dict(text="Ticket Promedio por Mes (KPI-7)", font=dict(color=TEXT_H, size=13), x=0.01),
    )
    return fig


# ─── 9.3 Vista Comparativa ───────────────────────────────────────────────────

def fig_categorias_bar(data: dict, top_n: int = 15) -> go.Figure:
    """Barras horizontales de ingresos por categoría."""
    cats = data.get("categorias", [])[:top_n]
    if not cats:
        return _base("Sin datos")
    cats_rev = list(reversed(cats))
    fig = _base()
    fig.add_trace(go.Bar(
        y=[c["categoria"]       for c in cats_rev],
        x=[c["ingresos_brl"]    for c in cats_rev],
        orientation="h",
        marker=dict(
            color=[c["contribucion_brl"] for c in cats_rev],
            colorscale=[[0, "rgba(139,92,246,0.5)"], [0.5, CYAN], [1, GREEN]],
            colorbar=dict(title="Contribución", tickprefix="R$", len=0.7),
            line=dict(color="rgba(0,0,0,0.2)", width=0.5),
        ),
        text=[f"R${c['ingresos_brl']:,.0f}" for c in cats_rev],
        textposition="outside",
        textfont=dict(color=TEXT, size=10),
        hovertemplate="<b>%{y}</b><br>Ingresos: R$ %{x:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        xaxis=dict(**AXIS_BASE, title="Ingresos (BRL)", tickprefix="R$ ", tickformat=",.0f"),
        yaxis=dict(**{k: v for k, v in AXIS_BASE.items() if k != "tickfont"}, title="", tickfont=dict(size=10)),
        title=dict(text="Ingresos por Categoría (KPI-3)", font=dict(color=TEXT_H, size=13), x=0.01),
        height=max(380, len(cats_rev) * 26),
    )
    return fig


def fig_margen_scatter(data: dict) -> go.Figure:
    """Scatter margen vs ingresos por categoría."""
    cats = data.get("categorias", [])
    if not cats:
        return _base("Sin datos")
    df = pd.DataFrame(cats)
    fig = _base()
    fig.add_trace(go.Scatter(
        x=df["ingresos_brl"],
        y=df["margen_pct"],
        mode="markers+text",
        text=df["categoria"],
        textposition="top center",
        textfont=dict(size=9, color=TEXT),
        marker=dict(
            size=df["total_items"] / df["total_items"].max() * 40 + 6,
            color=df["margen_pct"],
            colorscale=[[0, RED], [0.4, AMBER], [1, GREEN]],
            colorbar=dict(title="Margen %", ticksuffix="%"),
            opacity=0.85,
            line=dict(color="rgba(255,255,255,0.15)", width=1),
        ),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Ingresos: R$ %{x:,.0f}<br>"
            "Margen: %{y:.1f}%<extra></extra>"
        ),
    ))
    fig.update_layout(
        xaxis=dict(**AXIS_BASE, title="Ingresos Totales (BRL)", tickprefix="R$", tickformat=",.0f"),
        yaxis=dict(**AXIS_BASE, title="Margen % (KPI-6)", ticksuffix="%"),
        title=dict(text="Ingresos vs. Margen por Categoría", font=dict(color=TEXT_H, size=13), x=0.01),
        height=430,
    )
    return fig


def fig_metodos_pago_donut(data: dict) -> go.Figure:
    """Donut de distribución de métodos de pago."""
    pagos = data.get("metodos_pago", [])
    if not pagos:
        return _base("Sin datos")
    fig = _base()
    fig.add_trace(go.Pie(
        labels=[p["descripcion"] for p in pagos],
        values=[p["monto_total_brl"] for p in pagos],
        hole=0.62,
        marker=dict(colors=[CYAN, PURPLE, PINK, AMBER],
                    line=dict(color=BG, width=3)),
        textinfo="percent+label",
        textfont=dict(size=11, color=TEXT_H),
        hovertemplate="<b>%{label}</b><br>R$ %{value:,.0f}<br>%{percent}<extra></extra>",
        direction="clockwise",
    ))
    fig.update_layout(
        title=dict(text="Distribución Métodos de Pago (KPI-8)", font=dict(color=TEXT_H, size=13), x=0.01),
        showlegend=True,
        legend=dict(orientation="v", x=1.0, y=0.5, font=dict(color=TEXT)),
        annotations=[dict(
            text="Pago<br>Mix", x=0.5, y=0.5, font=dict(color=CYAN, size=13), showarrow=False
        )],
        height=350,
    )
    return fig


def fig_estados_mapa_calor(data: dict) -> go.Figure:
    """Heatmap ficticio: estados × ingresos (top 10)."""
    estados = data.get("estados", [])[:10]
    if not estados:
        return _base("Sin datos")
    fig = _base()
    estados_rev = list(reversed(estados))
    fig.add_trace(go.Bar(
        y=[e["estado"] for e in estados_rev],
        x=[e["ingresos_brl"] for e in estados_rev],
        orientation="h",
        marker=dict(
            color=[e["ingresos_brl"] for e in estados_rev],
            colorscale=[[0, "rgba(139,92,246,0.3)"], [1, CYAN]],
            line=dict(color="rgba(0,0,0,0.2)", width=0.5),
        ),
        text=[f"{e['participacion_pct']:.1f}%" for e in estados_rev],
        textposition="inside",
        textfont=dict(color="#000", size=10),
        hovertemplate="<b>%{y}</b><br>R$ %{x:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        xaxis=dict(**AXIS_BASE, title="Ingresos (BRL)", tickprefix="R$", tickformat=",.0f"),
        yaxis=dict(**AXIS_BASE),
        title=dict(text="Top 10 Estados por Ingresos (KPI-4)", font=dict(color=TEXT_H, size=13), x=0.01),
        height=340,
    )
    return fig


def fig_ticket_estado_barras(data: dict) -> go.Figure:
    """Ticket promedio por estado."""
    estados = sorted(data.get("estados", []), key=lambda e: e["ticket_promedio_brl"], reverse=True)[:15]
    if not estados:
        return _base("Sin datos")
    colores = [GREEN if e["ticket_promedio_brl"] >= 160
               else AMBER if e["ticket_promedio_brl"] >= 120
               else RED for e in estados]
    fig = _base()
    fig.add_trace(go.Bar(
        x=[e["estado"] for e in estados],
        y=[e["ticket_promedio_brl"] for e in estados],
        marker=dict(color=colores, line=dict(color="rgba(0,0,0,0.2)", width=0.5)),
        name="Ticket",
        hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>",
    ))
    fig.add_hline(y=300, line=dict(color=GREEN, width=1, dash="dot"), annotation_text="Meta R$300")
    fig.add_hline(y=120, line=dict(color=AMBER, width=1, dash="dot"), annotation_text="Umbral R$200")
    fig.update_layout(
        xaxis=dict(**AXIS_BASE, title="Estado (UF)"),
        yaxis=dict(**AXIS_BASE, title="Ticket Promedio (BRL)", tickprefix="R$ "),
        title=dict(text="Ticket Promedio por Estado (KPI-7)", font=dict(color=TEXT_H, size=13), x=0.01),
        bargap=0.3,
    )
    return fig


def fig_entrega_region(data: dict) -> go.Figure:
    """Tiempo promedio de entrega por región."""
    estados = data.get("estados", [])
    if not estados:
        return _base("Sin datos")
    df = pd.DataFrame(estados)
    if "region" not in df or "tiempo_entrega_prom" not in df:
        return _base("Sin datos de entrega")
    df_r = df.groupby("region")["tiempo_entrega_prom"].mean().reset_index()
    df_r = df_r.sort_values("tiempo_entrega_prom")
    colores = [GREEN if v <= 10 else AMBER if v <= 15 else RED
               for v in df_r["tiempo_entrega_prom"]]
    fig = _base()
    fig.add_trace(go.Bar(
        x=df_r["region"],
        y=df_r["tiempo_entrega_prom"],
        marker=dict(color=colores),
        text=[f"{v:.1f}d" for v in df_r["tiempo_entrega_prom"]],
        textposition="outside",
        textfont=dict(color=TEXT_H),
        hovertemplate="<b>%{x}</b><br>%{y:.1f} días<extra></extra>",
    ))
    fig.add_hline(y=10, line=dict(color=GREEN, width=1, dash="dot"), annotation_text="Meta 10d")
    fig.add_hline(y=15, line=dict(color=AMBER, width=1, dash="dot"), annotation_text="Umbral 15d")
    fig.update_layout(
        xaxis=dict(**AXIS_BASE, title="Región"),
        yaxis=dict(**AXIS_BASE, title="Días promedio"),
        title=dict(text="Tiempo de Entrega por Región (KPI-10)", font=dict(color=TEXT_H, size=13), x=0.01),
        bargap=0.3,
    )
    return fig


# ─── 9.4 KPI Semaforizado — Gauge ─────────────────────────────────────────────

_COLOR_MAP = {"green": GREEN, "yellow": AMBER, "red": RED}


def fig_gauge(kpi: dict) -> go.Figure:
    color  = _COLOR_MAP.get(kpi["color"], CYAN)
    valor  = kpi["valor_actual"]
    v_meta = kpi["meta_verde"]
    unidad = kpi["unidad"]

    # Para KPIs "cuanto menor mejor", invertir la escala
    inv = kpi["kpi_id"] in ("KPI-9", "KPI-10")
    max_val = v_meta * 3 if not inv else kpi["meta_amarilla"] * 2.5

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=valor,
        number=dict(
            prefix="" if unidad in ("%", "días") else "R$ ",
            suffix=f" {unidad}" if unidad in ("%", "días") else "",
            font=dict(size=28, color=color, family="Inter"),
            valueformat=",.1f" if unidad == "%" else ",.0f",
        ),
        delta=dict(
            reference=v_meta,
            increasing=dict(color=RED if inv else GREEN),
            decreasing=dict(color=GREEN if inv else RED),
            font=dict(size=13),
        ),
        gauge=dict(
            axis=dict(
                range=[0, max_val],
                tickfont=dict(color=TEXT, size=9),
                tickcolor=GRID,
            ),
            bar=dict(color=color, thickness=0.25),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            steps=[
                dict(range=[0, kpi["meta_verde"]] if not inv else [kpi["meta_verde"], max_val],
                     color="rgba(16,185,129,0.12)"),
                dict(range=[kpi["meta_verde"], kpi["meta_amarilla"]] if not inv
                     else [kpi["meta_amarilla"], kpi["meta_verde"]],
                     color="rgba(245,158,11,0.12)"),
            ],
            threshold=dict(
                line=dict(color=color, width=3),
                thickness=0.8,
                value=valor,
            ),
        ),
        title=dict(text=kpi["nombre"], font=dict(size=13, color=TEXT_H)),
    ))
    base_no_margin = {k: v for k, v in BASE_LAYOUT.items() if k != "margin"}
    fig.update_layout(
        **base_no_margin,
        height=240,
        margin=dict(l=20, r=20, t=50, b=10),
    )
    return fig


def fig_semaforo_hist(kpi: dict) -> go.Figure:
    """Línea histórica del KPI semaforizado."""
    pts = kpi.get("historico", [])
    if not pts:
        fig = _base()
        fig.update_layout(height=120)
        return fig
    color = _COLOR_MAP.get(kpi["color"], CYAN)
    fig = _base()
    fig.add_trace(go.Scatter(
        x=[p["periodo"] for p in pts],
        y=[p["valor"]   for p in pts],
        mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=f"rgba({','.join(str(int(c)) for c in _hex_to_rgb(color))},0.08)",
        hovertemplate="%{x}: %{y:.1f}<extra></extra>",
    ))
    fig.add_hline(y=kpi["meta_verde"],
                  line=dict(color=GREEN, width=1, dash="dot"))
    fig.update_layout(
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        height=80,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
    )
    return fig


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
