"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Olist BI Dashboard — Capítulo 9                                            ║
║  9.1 Resumen Ejecutivo · 9.2 Vistas Acumulativas · 9.3 Vista Comparativa   ║
║  9.4 KPI Semaforizado  · 9.5 Filtros y Segmentadores                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Compatibilidad Python 3.14: pkgutil.find_loader fue eliminado ─────────────
# Dash 2.x lo usa internamente; este parche lo restaura antes de que Dash cargue.
import pkgutil as _pkgutil
if not hasattr(_pkgutil, "find_loader"):
    import importlib.util as _ilu
    def _find_loader(name):
        try:
            spec = _ilu.find_spec(name)
            return spec.loader if spec else None
        except (ModuleNotFoundError, ValueError):
            return None
    _pkgutil.find_loader = _find_loader

from datetime import datetime, date
import dash
from dash import dcc, html, Input, Output, State, dash_table, callback
import dash_bootstrap_components as dbc
from dotenv import load_dotenv

load_dotenv()

from dashboard import api_client as api
from dashboard.layouts import charts as ch

# ═══════════════════════════════════════════════════════════════════════════════
# Inicialización
# ═══════════════════════════════════════════════════════════════════════════════

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.CYBORG,
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap",
    ],
    suppress_callback_exceptions=True,
    title="Olist BI · Capítulo 9",
    update_title=None,
)
server = app.server

# ═══════════════════════════════════════════════════════════════════════════════
# Helpers de layout
# ═══════════════════════════════════════════════════════════════════════════════


def _kpi_card(kpi: dict) -> html.Div:
    delta = kpi.get("variacion_pct", 0)
    tend = kpi.get("tendencia", "stable")
    icon = "▲" if tend == "up" else "▼" if tend == "down" else "─"
    cls = (
        "delta-up"
        if tend == "up"
        else "delta-down" if tend == "down" else "delta-stable"
    )
    val = kpi["valor"]
    unit = kpi.get("unidad", "")
    fmt = f"R$ {val:,.2f}" if unit == "BRL" else f"{val:,.1f} {unit}"
    return html.Div(
        [
            html.Div(kpi["kpi_id"], className="kpi-id"),
            html.Div(kpi["nombre"], className="kpi-name"),
            html.Div(
                [
                    html.Span(fmt, className="kpi-value"),
                ]
            ),
            html.Div(
                [
                    html.Span(
                        f"{icon} {abs(delta):.1f}% vs período anterior", className=cls
                    ),
                ],
                className="kpi-delta",
            ),
        ],
        className="kpi-card",
    )


def _semaforo_card(s: dict) -> dbc.Col:
    color = s["color"]
    color_cls = f"semaforo-{color}"
    ind_cls = f"ind-{color}"
    label_map = {"green": "● ÓPTIMO", "yellow": "● ALERTA", "red": "● CRÍTICO"}
    label_col = {"green": "#10b981", "yellow": "#f59e0b", "red": "#ef4444"}
    return dbc.Col(
        html.Div(
            [
                dcc.Graph(figure=ch.fig_gauge(s), config={"displayModeBar": False}),
                html.Div(
                    [
                        html.Span(className=f"semaforo-indicator {ind_cls}"),
                        html.Span(
                            label_map[color],
                            style={
                                "color": label_col[color],
                                "fontSize": "0.72rem",
                                "letterSpacing": "1px",
                                "fontFamily": "Courier New",
                            },
                        ),
                    ],
                    style={"textAlign": "center", "marginTop": "4px"},
                ),
                html.Div(
                    s["descripcion_meta"],
                    style={
                        "textAlign": "center",
                        "fontSize": "0.68rem",
                        "color": "#64748b",
                        "marginTop": "4px",
                    },
                ),
                html.Div(
                    s["formula"],
                    style={
                        "textAlign": "center",
                        "fontSize": "0.65rem",
                        "color": "#334155",
                        "fontFamily": "Courier New",
                        "marginTop": "4px",
                    },
                ),
                dcc.Graph(
                    figure=ch.fig_semaforo_hist(s),
                    config={"displayModeBar": False},
                    style={"marginTop": "4px"},
                ),
            ],
            className=f"semaforo-card {color_cls}",
        ),
        lg=3,
        md=6,
        sm=12,
    )


def _section_title(icon: str, texto: str, badge: str) -> html.Div:
    return html.Div(
        [
            html.Span(
                f"{icon} {texto}", style={"fontWeight": "700", "fontSize": "1rem"}
            ),
            html.Span(badge, className="section-badge", style={"marginLeft": "10px"}),
        ],
        className="section-title",
        style={"marginBottom": "18px"},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 9.5 — Panel de filtros (persiste en todas las tabs)
# ═══════════════════════════════════════════════════════════════════════════════


def _filter_panel() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div("PERÍODO", className="filter-label"),
                    dcc.DatePickerRange(
                        id="filter-dates",
                        min_date_allowed=date(2017, 1, 1),
                        max_date_allowed=date(2018, 9, 30),
                        start_date=date(2017, 1, 1),
                        end_date=date(2018, 9, 30),
                        display_format="MMM YY",
                        start_date_placeholder_text="Inicio",
                        end_date_placeholder_text="Fin",
                        calendar_orientation="horizontal",
                        number_of_months_shown=2,
                        with_portal=False,
                        style={"fontSize": "0.8rem", "minWidth": "240px"},
                    ),
                ],
                className="filter-group",
            ),
            html.Div(
                [
                    html.Div("REGIÓN", className="filter-label"),
                    dcc.Dropdown(
                        id="filter-region",
                        options=[
                            {"label": r, "value": r}
                            for r in [
                                "Sudeste",
                                "Sul",
                                "Centro-Oeste",
                                "Nordeste",
                                "Norte",
                            ]
                        ],
                        placeholder="Todas las regiones",
                        clearable=True,
                        style={"width": "175px"},
                        optionHeight=34,
                    ),
                ],
                className="filter-group",
            ),
            html.Div(
                [
                    html.Div("ESTADO (UF)", className="filter-label"),
                    dcc.Dropdown(
                        id="filter-estado",
                        options=[
                            {"label": e, "value": e}
                            for e in [
                                "SP",
                                "RJ",
                                "MG",
                                "RS",
                                "PR",
                                "SC",
                                "BA",
                                "GO",
                                "ES",
                                "PE",
                                "CE",
                                "DF",
                                "AM",
                                "PA",
                                "RO",
                                "AC",
                                "AP",
                                "RR",
                                "TO",
                                "MA",
                                "PB",
                                "RN",
                                "AL",
                                "SE",
                                "PI",
                                "MT",
                                "MS",
                            ]
                        ],
                        placeholder="Todos",
                        clearable=True,
                        style={"width": "130px"},
                        optionHeight=34,
                    ),
                ],
                className="filter-group",
            ),
            html.Div(
                [
                    html.Div("CATEGORÍA", className="filter-label"),
                    dcc.Dropdown(
                        id="filter-categoria",
                        options=[
                            {"label": c, "value": c}
                            for c in [
                                "Juguetes",
                                "Salud y Belleza",
                                "Accesorios de Computadora",
                                "Muebles y Decoración",
                                "Deportes y Ocio",
                                "Moda y Accesorios",
                                "Telefonía",
                                "Artículos del Hogar",
                                "Electrónica General",
                                "Bebé",
                                "Relojes y Regalos",
                                "Papelería",
                                "Herramientas de Jardín",
                                "Automotriz",
                                "Cama, Baño y Mesa",
                                "Perfumería",
                                "Libros",
                            ]
                        ],
                        placeholder="Todas",
                        clearable=True,
                        style={"width": "210px"},
                        optionHeight=34,
                    ),
                ],
                className="filter-group",
            ),
            html.Div(
                [
                    html.Div("MÉTODO DE PAGO", className="filter-label"),
                    dcc.Dropdown(
                        id="filter-metodo",
                        options=[
                            {"label": "Tarjeta Crédito", "value": "credit_card"},
                            {"label": "Boleto Bancário", "value": "boleto"},
                            {"label": "Vale Descuento", "value": "voucher"},
                            {"label": "Tarjeta Débito", "value": "debit_card"},
                        ],
                        placeholder="Todos",
                        clearable=True,
                        style={"width": "175px"},
                        optionHeight=34,
                    ),
                ],
                className="filter-group",
            ),
            dbc.Button(
                "↺ Actualizar",
                id="btn-refresh",
                color="info",
                outline=True,
                size="sm",
                style={
                    "alignSelf": "flex-end",
                    "fontSize": "0.78rem",
                    "border": "1px solid rgba(0,245,255,0.4)",
                    "color": "#00f5ff",
                    "background": "rgba(0,245,255,0.06)",
                },
            ),
            html.Div(
                id="api-status", style={"alignSelf": "flex-end", "fontSize": "0.7rem"}
            ),
        ],
        id="filter-panel",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Layout principal
# ═══════════════════════════════════════════════════════════════════════════════

app.layout = html.Div(
    [
        dcc.Interval(id="interval-clock", interval=1000, n_intervals=0),
        dcc.Store(id="store-resumen"),
        dcc.Store(id="store-acumulativas"),
        dcc.Store(id="store-comparativa"),
        dcc.Store(id="store-semaforizados"),
        # ── Header ───────────────────────────────────────────────────────────────
        html.Div(
            [
                html.Div(
                    [
                        html.Div("OLIST BI", className="header-logo"),
                        html.Div(
                            "SISTEMA DE INTELIGENCIA DE NEGOCIOS · SI807U",
                            className="header-subtitle",
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Span(
                            "CAP. 9 · DASHBOARD EJECUTIVO",
                            style={
                                "fontSize": "0.7rem",
                                "color": "#64748b",
                                "letterSpacing": "2px",
                                "marginRight": "20px",
                            },
                        ),
                        html.Div(id="clock-display", className="header-time"),
                    ],
                    style={"display": "flex", "alignItems": "center"},
                ),
            ],
            id="header",
        ),
        # ── Filtros 9.5 ──────────────────────────────────────────────────────────
        _filter_panel(),
        # ── Tabs ─────────────────────────────────────────────────────────────────
        dcc.Tabs(
            id="main-tabs",
            value="tab-resumen",
            className="tab-nav",
            children=[
                dcc.Tab(
                    label="📊  Resumen Ejecutivo",
                    value="tab-resumen",
                    className="dash-tab",
                    selected_className="dash-tab--selected",
                ),
                dcc.Tab(
                    label="📈  Vistas Acumulativas",
                    value="tab-acumulativas",
                    className="dash-tab",
                    selected_className="dash-tab--selected",
                ),
                dcc.Tab(
                    label="⚖️  Vista Comparativa",
                    value="tab-comparativa",
                    className="dash-tab",
                    selected_className="dash-tab--selected",
                ),
                dcc.Tab(
                    label="🚦  KPI Semaforizado",
                    value="tab-semaforo",
                    className="dash-tab",
                    selected_className="dash-tab--selected",
                ),
            ],
        ),
        html.Div(
            id="tab-content", className="tab-content", style={"padding": "20px 24px"}
        ),
    ],
    style={"minHeight": "100vh"},
)


# ═══════════════════════════════════════════════════════════════════════════════
# Callbacks
# ═══════════════════════════════════════════════════════════════════════════════


# ── Reloj ─────────────────────────────────────────────────────────────────────
@app.callback(
    Output("clock-display", "children"), Input("interval-clock", "n_intervals")
)
def update_clock(_):
    return datetime.now().strftime("%Y-%m-%d  %H:%M:%S")


# ── Carga de datos al pulsar Actualizar o al cargar la página ─────────────────
@app.callback(
    Output("store-resumen", "data"),
    Output("store-acumulativas", "data"),
    Output("store-comparativa", "data"),
    Output("store-semaforizados", "data"),
    Output("api-status", "children"),
    Input("btn-refresh", "n_clicks"),
    State("filter-dates", "start_date"),
    State("filter-dates", "end_date"),
    State("filter-region", "value"),
    State("filter-estado", "value"),
    State("filter-categoria", "value"),
    State("filter-metodo", "value"),
    prevent_initial_call=False,
)
def load_data(_, fi, ff, region, estado, categoria, metodo):
    kwargs = {
        k: v
        for k, v in dict(
            fecha_inicio=fi,
            fecha_fin=ff,
            region=region,
            estado=estado,
            categoria=categoria,
            metodo_pago=metodo,
        ).items()
        if v
    }

    healthy = api.check_api_health()
    status_el = html.Span(
        "● API conectada" if healthy else "● API offline — usando datos simulados",
        style={"color": "#10b981" if healthy else "#f59e0b"},
    )

    resumen = api.get_resumen_ejecutivo(**kwargs) or _fallback_resumen()
    acumulativas = (
        api.get_acumulativas(**{k: v for k, v in kwargs.items() if k != "categoria"})
        or _fallback_acumulativas()
    )
    comparativa = (
        api.get_comparativa(**{k: v for k, v in kwargs.items() if k != "metodo_pago"})
        or _fallback_comparativa()
    )
    semaforos = (
        api.get_semaforizados(
            **{k: v for k, v in kwargs.items() if k in ("fecha_inicio", "fecha_fin")}
        )
        or _fallback_semaforizados()
    )

    return resumen, acumulativas, comparativa, semaforos, status_el


# ── Renderizado de tabs ───────────────────────────────────────────────────────
@app.callback(
    Output("tab-content", "children"),
    Input("main-tabs", "value"),
    Input("store-resumen", "data"),
    Input("store-acumulativas", "data"),
    Input("store-comparativa", "data"),
    Input("store-semaforizados", "data"),
)
def render_tab(tab, resumen, acum, comp, sema):
    if tab == "tab-resumen":
        return _layout_resumen(resumen or {})
    if tab == "tab-acumulativas":
        return _layout_acumulativas(acum or {})
    if tab == "tab-comparativa":
        return _layout_comparativa(comp or {})
    if tab == "tab-semaforo":
        return _layout_semaforo(sema or {})
    return html.Div("Selecciona una pestaña.")


# ═══════════════════════════════════════════════════════════════════════════════
# 9.1 Resumen Ejecutivo
# ═══════════════════════════════════════════════════════════════════════════════


def _layout_resumen(data: dict) -> html.Div:
    kpis = data.get("kpis", [])
    total_p = data.get("total_pedidos", 0)
    total_i = data.get("total_ingresos_brl", 0)
    fi = data.get("periodo_inicio", "—")
    ff = data.get("periodo_fin", "—")
    top_cli = data.get("top_clientes", [])

    # Barra de resumen
    resumen_bar = html.Div(
        [
            html.Div(
                [
                    html.Div(f"{total_p:,.0f}", className="summary-val"),
                    html.Div("Total Pedidos", className="summary-lbl"),
                ],
                className="summary-item",
            ),
            html.Div(
                [
                    html.Div(f"R$ {total_i:,.0f}", className="summary-val"),
                    html.Div("Ingresos Totales", className="summary-lbl"),
                ],
                className="summary-item",
            ),
            html.Div(
                [
                    html.Div(
                        str(fi)[:7] if fi != "—" else "—",
                        className="summary-val",
                        style={"fontSize": "1rem"},
                    ),
                    html.Div("Período inicio", className="summary-lbl"),
                ],
                className="summary-item",
            ),
            html.Div(
                [
                    html.Div(
                        str(ff)[:7] if ff != "—" else "—",
                        className="summary-val",
                        style={"fontSize": "1rem"},
                    ),
                    html.Div("Período fin", className="summary-lbl"),
                ],
                className="summary-item",
            ),
        ],
        className="summary-bar",
    )

    # Tarjetas KPI
    kpi_row = dbc.Row(
        [dbc.Col(_kpi_card(k), lg=2, md=4, sm=6) for k in kpis],
        className="g-3",
        style={"marginBottom": "20px"},
    )

    # Tabla de top clientes
    table = dash_table.DataTable(
        data=top_cli,
        columns=[
            {"name": "ID Cliente", "id": "customer_id"},
            {"name": "Ciudad", "id": "ciudad"},
            {"name": "Estado", "id": "estado"},
            {"name": "Nº Pedidos", "id": "num_pedidos"},
            {
                "name": "Ingreso Acumulado R$",
                "id": "ingreso_acumulado_brl",
                "type": "numeric",
                "format": {"specifier": ",.2f"},
            },
            {
                "name": "Ticket Prom. R$",
                "id": "ticket_promedio_brl",
                "type": "numeric",
                "format": {"specifier": ",.2f"},
            },
        ],
        style_table={"overflowX": "auto", "borderRadius": "10px"},
        style_header={
            "backgroundColor": "rgba(0,245,255,0.08)",
            "color": "#00f5ff",
            "fontFamily": "Courier New",
            "fontSize": "0.7rem",
            "letterSpacing": "1px",
            "border": "none",
            "textTransform": "uppercase",
        },
        style_cell={
            "backgroundColor": "#080f1e",
            "color": "#e2e8f0",
            "border": "1px solid rgba(0,245,255,0.06)",
            "fontSize": "0.82rem",
            "padding": "10px 14px",
            "fontFamily": "Inter, sans-serif",
        },
        style_data_conditional=[
            {"if": {"row_index": 0}, "border-left": "3px solid #00f5ff"},
            {"if": {"row_index": 1}, "border-left": "3px solid #8b5cf6"},
            {"if": {"row_index": 2}, "border-left": "3px solid #f43f5e"},
        ],
        page_size=10,
        sort_action="native",
    )

    return html.Div(
        [
            _section_title("📊", "Resumen Ejecutivo", "9.1"),
            resumen_bar,
            _section_title(
                "🔢", "Indicadores Clave (KPIs)", "KPI · Período seleccionado"
            ),
            kpi_row,
            _section_title(
                "🏆",
                "Top Clientes por Ingreso Acumulado (KPI-12)",
                "Q5 · Segmentación VIP",
            ),
            html.Div(table, className="chart-card"),
            html.Div(
                [
                    html.Span(
                        "⚠ Nota: ", style={"color": "#f59e0b", "fontWeight": "700"}
                    ),
                    html.Span(
                        "Los márgenes (KPI-5, KPI-6) utilizan costos estimados (df_Products_with_cost.csv). "
                        "No representan COGS real del ERP. Ver Anexo A del informe.",
                        style={"color": "#64748b", "fontSize": "0.72rem"},
                    ),
                ],
                style={
                    "marginTop": "16px",
                    "padding": "10px 14px",
                    "border": "1px solid rgba(245,158,11,0.2)",
                    "borderRadius": "6px",
                    "background": "rgba(245,158,11,0.04)",
                },
            ),
        ]
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 9.2 Vistas Acumulativas
# ═══════════════════════════════════════════════════════════════════════════════


def _layout_acumulativas(data: dict) -> html.Div:
    return html.Div(
        [
            _section_title("📈", "Vistas Acumulativas", "9.2"),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    "INGRESOS MENSUALES POR REGIÓN",
                                    className="chart-title",
                                ),
                                dcc.Graph(
                                    figure=ch.fig_ingresos_area(data),
                                    config={"displayModeBar": False},
                                    style={"height": "340px"},
                                ),
                            ],
                            className="chart-card",
                        ),
                        lg=8,
                        md=12,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    "INGRESOS ACUMULADOS", className="chart-title"
                                ),
                                dcc.Graph(
                                    figure=ch.fig_acumulado_line(data),
                                    config={"displayModeBar": False},
                                    style={"height": "340px"},
                                ),
                            ],
                            className="chart-card",
                        ),
                        lg=4,
                        md=12,
                    ),
                ],
                className="g-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    "PEDIDOS POR MES (KPI-2)", className="chart-title"
                                ),
                                dcc.Graph(
                                    figure=ch.fig_pedidos_bar(data),
                                    config={"displayModeBar": False},
                                    style={"height": "280px"},
                                ),
                            ],
                            className="chart-card",
                        ),
                        lg=4,
                        md=12,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    "TICKET PROMEDIO MENSUAL (KPI-5)",
                                    className="chart-title",
                                ),
                                dcc.Graph(
                                    figure=ch.fig_ticket_line(data),
                                    config={"displayModeBar": False},
                                    style={"height": "280px"},
                                ),
                            ],
                            className="chart-card",
                        ),
                        lg=4,
                        md=12,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    "MARGEN LOGÍSTICO % MENSUAL (KPI-4)", className="chart-title"
                                ),
                                dcc.Graph(
                                    figure=ch.fig_margen_line(data),
                                    config={"displayModeBar": False},
                                    style={"height": "280px"},
                                ),
                            ],
                            className="chart-card",
                        ),
                        lg=4,
                        md=12,
                    ),
                ],
                className="g-3",
            ),
        ]
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 9.3 Vista Comparativa
# ═══════════════════════════════════════════════════════════════════════════════


def _layout_comparativa(data: dict) -> html.Div:
    return html.Div(
        [
            _section_title("⚖️", "Vista Comparativa", "9.3"),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    "VENTAS vs. MARGEN LOGÍSTICO POR CATEGORÍA (KPI-7 / KPI-3)",
                                    className="chart-title",
                                ),
                                dcc.Graph(
                                    figure=ch.fig_margen_scatter(data),
                                    config={"displayModeBar": False},
                                ),
                            ],
                            className="chart-card",
                        ),
                        lg=7,
                        md=12,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    "DISTRIBUCIÓN MÉTODOS DE PAGO (KPI-9)",
                                    className="chart-title",
                                ),
                                dcc.Graph(
                                    figure=ch.fig_metodos_pago_donut(data),
                                    config={"displayModeBar": False},
                                ),
                            ],
                            className="chart-card",
                        ),
                        lg=5,
                        md=12,
                    ),
                ],
                className="g-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    "VENTAS POR CATEGORÍA DE PRODUCTO (KPI-7)",
                                    className="chart-title",
                                ),
                                dcc.Graph(
                                    figure=ch.fig_categorias_bar(data),
                                    config={"displayModeBar": False},
                                ),
                            ],
                            className="chart-card",
                        ),
                        lg=6,
                        md=12,
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        "INGRESOS POR ESTADO / REGIÓN (KPI-8)",
                                        className="chart-title",
                                    ),
                                    dcc.Graph(
                                        figure=ch.fig_estados_mapa_calor(data),
                                        config={"displayModeBar": False},
                                    ),
                                ],
                                className="chart-card",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        "TIEMPO PROMEDIO ENTREGA POR REGIÓN (KPI-10)",
                                        className="chart-title",
                                    ),
                                    dcc.Graph(
                                        figure=ch.fig_entrega_region(data),
                                        config={"displayModeBar": False},
                                    ),
                                ],
                                className="chart-card",
                            ),
                        ],
                        lg=6,
                        md=12,
                    ),
                ],
                className="g-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    "TICKET PROMEDIO POR ESTADO (KPI-5) — Semáforo por umbral R$300",
                                    className="chart-title",
                                ),
                                dcc.Graph(
                                    figure=ch.fig_ticket_estado_barras(data),
                                    config={"displayModeBar": False},
                                    style={"height": "320px"},
                                ),
                            ],
                            className="chart-card",
                        ),
                        lg=12,
                    ),
                ],
                className="g-3",
            ),
        ]
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 9.4 KPI Semaforizado
# ═══════════════════════════════════════════════════════════════════════════════


def _layout_semaforo(data: dict) -> html.Div:
    semaforos = data.get("semaforos", [])
    resumen = data.get("resumen_colores", {"green": 0, "yellow": 0, "red": 0})

    # Barra de estado global
    total = sum(resumen.values()) or 1
    estado_bar = html.Div(
        [
            html.Div(
                [
                    html.Div(
                        str(resumen.get("green", 0)),
                        className="summary-val",
                        style={"color": "#10b981"},
                    ),
                    html.Div("ÓPTIMO", className="summary-lbl"),
                ],
                className="summary-item",
            ),
            html.Div(
                [
                    html.Div(
                        str(resumen.get("yellow", 0)),
                        className="summary-val",
                        style={"color": "#f59e0b"},
                    ),
                    html.Div("ALERTA", className="summary-lbl"),
                ],
                className="summary-item",
            ),
            html.Div(
                [
                    html.Div(
                        str(resumen.get("red", 0)),
                        className="summary-val",
                        style={"color": "#ef4444"},
                    ),
                    html.Div("CRÍTICO", className="summary-lbl"),
                ],
                className="summary-item",
            ),
            html.Div(
                [
                    html.Div(
                        str(total), className="summary-val", style={"color": "#00f5ff"}
                    ),
                    html.Div("KPIs MONITOREADOS", className="summary-lbl"),
                ],
                className="summary-item",
            ),
        ],
        className="summary-bar",
        style={"marginBottom": "24px"},
    )

    gauge_row = dbc.Row(
        [_semaforo_card(s) for s in semaforos],
        className="g-3",
        style={"marginBottom": "24px"},
    )

    # Tabla de metas
    meta_tabla = dash_table.DataTable(
        data=[
            {
                "KPI": s["kpi_id"],
                "Nombre": s["nombre"],
                "Valor Actual": f"{s['valor_actual']:,.1f} {s['unidad']}",
                "Meta Óptima": f"{s['meta_verde']:,.0f} {s['unidad']}",
                "Umbral Alerta": f"{s['meta_amarilla']:,.0f} {s['unidad']}",
                "Estado": {
                    "green": "● ÓPTIMO",
                    "yellow": "● ALERTA",
                    "red": "● CRÍTICO",
                }.get(s["color"], "—"),
                "Fórmula": s["formula"],
            }
            for s in semaforos
        ],
        columns=[
            {"name": c, "id": c}
            for c in [
                "KPI",
                "Nombre",
                "Valor Actual",
                "Meta Óptima",
                "Umbral Alerta",
                "Estado",
                "Fórmula",
            ]
        ],
        style_table={"overflowX": "auto", "borderRadius": "10px"},
        style_header={
            "backgroundColor": "rgba(0,245,255,0.08)",
            "color": "#00f5ff",
            "fontFamily": "Courier New",
            "fontSize": "0.7rem",
            "letterSpacing": "1px",
            "border": "none",
            "textTransform": "uppercase",
        },
        style_cell={
            "backgroundColor": "#080f1e",
            "color": "#e2e8f0",
            "border": "1px solid rgba(0,245,255,0.06)",
            "fontSize": "0.82rem",
            "padding": "10px 14px",
        },
        style_data_conditional=[
            {
                "if": {
                    "filter_query": '{Estado} contains "ÓPTIMO"',
                    "column_id": "Estado",
                },
                "color": "#10b981",
                "fontWeight": "700",
            },
            {
                "if": {
                    "filter_query": '{Estado} contains "ALERTA"',
                    "column_id": "Estado",
                },
                "color": "#f59e0b",
                "fontWeight": "700",
            },
            {
                "if": {
                    "filter_query": '{Estado} contains "CRÍTICO"',
                    "column_id": "Estado",
                },
                "color": "#ef4444",
                "fontWeight": "700",
            },
        ],
    )

    return html.Div(
        [
            _section_title("🚦", "KPI Semaforizado", "9.4"),
            estado_bar,
            _section_title("", "Gauges por KPI", "Período seleccionado"),
            gauge_row,
            _section_title(
                "", "Tabla de Metas y Estado", "Umbrales según plan estratégico"
            ),
            html.Div(meta_tabla, className="chart-card"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(
                                "Regla crítica: ",
                                style={"color": "#f59e0b", "fontWeight": "700"},
                            ),
                            html.Span(
                                "KPI-3 (Contribución Logística) = precio − freight_value. "
                                "No incluye COGS real (limitación del dataset Olist). "
                                "KPI-5 y KPI-6 son no-aditivos: siempre se recalculan desde los agregados base. "
                                "Fuente: curated_fact_payment · curated_fact_orderitem · curated_fact_delivery (Hive).",
                                style={"color": "#64748b", "fontSize": "0.72rem"},
                            ),
                        ],
                        style={
                            "padding": "10px 14px",
                            "border": "1px solid rgba(245,158,11,0.2)",
                            "borderRadius": "6px",
                            "background": "rgba(245,158,11,0.04)",
                            "marginTop": "16px",
                        },
                    ),
                ]
            ),
        ]
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Datos de fallback (cuando la API no está disponible)
# ═══════════════════════════════════════════════════════════════════════════════


def _fallback_resumen() -> dict:
    # Valores basados en datos reales Olist 2016-2018 (Kaggle):
    # 89,316 pedidos · R$ 30,447,872 totales · 12 días entrega · 0.46% cancelación
    return {
        "periodo_inicio": "2016-09-01",
        "periodo_fin":    "2018-09-30",
        "total_pedidos":  89_316,
        "total_ingresos_brl": 30_447_872.89,
        "kpis": [
            {"kpi_id":"KPI-1",  "nombre":"Valor Total Pagado",       "valor":30_447_872.89, "unidad":"BRL",      "variacion_pct":8.3,   "tendencia":"up"},
            {"kpi_id":"KPI-2",  "nombre":"Cantidad Ítems Vendidos",  "valor":112_650.0,     "unidad":"unidades", "variacion_pct":5.1,   "tendencia":"up"},
            {"kpi_id":"KPI-3",  "nombre":"Contribución Logística",   "valor":26_492_673.72, "unidad":"BRL",      "variacion_pct":2.4,   "tendencia":"up"},
            {"kpi_id":"KPI-4",  "nombre":"Margen Logístico %",       "valor":87.01,         "unidad":"%",        "variacion_pct":0.3,   "tendencia":"up"},
            {"kpi_id":"KPI-5",  "nombre":"Ticket Promedio/Pedido",   "valor":340.87,        "unidad":"BRL",      "variacion_pct":-2.1,  "tendencia":"down"},
            {"kpi_id":"KPI-6",  "nombre":"Tasa Cancelación",         "valor":0.46,          "unidad":"%",        "variacion_pct":-0.04, "tendencia":"down"},
            {"kpi_id":"KPI-10", "nombre":"Tiempo Prom. Entrega",     "valor":12.0,          "unidad":"días",     "variacion_pct":-1.5,  "tendencia":"down"},
        ],
        "top_clientes": [
            {
                "customer_id": f"CLT{i:04d}",
                "ciudad": c,
                "estado": e,
                "num_pedidos": n,
                "ingreso_acumulado_brl": v,
                "ticket_promedio_brl": v / n,
            }
            for i, (c, e, n, v) in enumerate(
                [
                    ("São Paulo", "SP", 8, 2140.50),
                    ("Rio de Janeiro", "RJ", 5, 1890.20),
                    ("Belo Horizonte", "MG", 6, 1750.80),
                    ("Curitiba", "PR", 4, 1620.00),
                    ("Porto Alegre", "RS", 5, 1510.30),
                    ("Salvador", "BA", 3, 1400.60),
                    ("Brasília", "DF", 4, 1350.90),
                    ("Fortaleza", "CE", 3, 1280.40),
                    ("Recife", "PE", 3, 1200.10),
                    ("Goiânia", "GO", 2, 980.70),
                ],
                1,
            )
        ],
    }


def _fallback_acumulativas() -> dict:
    import random, math

    random.seed(42)
    meses = [
        (2017, m, n)
        for m, n in enumerate(
            [
                "Enero",
                "Febrero",
                "Marzo",
                "Abril",
                "Mayo",
                "Junio",
                "Julio",
                "Agosto",
                "Septiembre",
                "Octubre",
                "Noviembre",
                "Diciembre",
            ],
            1,
        )
    ] + [
        (2018, m, n)
        for m, n in enumerate(
            [
                "Enero",
                "Febrero",
                "Marzo",
                "Abril",
                "Mayo",
                "Junio",
                "Julio",
                "Agosto",
                "Septiembre",
            ],
            1,
        )
    ]
    regiones = ["Sudeste", "Sul", "Nordeste", "Centro-Oeste", "Norte"]
    pesos_r = [0.50, 0.18, 0.16, 0.10, 0.06]
    ing_mensual = []
    base = 18_000
    for anio, mes, nombre in meses:
        tendencia = 1 + (anio - 2017) * 0.3 + (mes - 1) * 0.015
        for reg, peso in zip(regiones, pesos_r):
            ing = round((base + random.gauss(0, 2000)) * tendencia * peso, 2)
            ing_mensual.append(
                {
                    "periodo": f"{anio}-{mes:02d}",
                    "anio": anio,
                    "mes": mes,
                    "nombre_mes": nombre,
                    "region": reg,
                    "num_pedidos": random.randint(30, 200),
                    "ingresos_brl": max(1000, ing),
                    "ticket_promedio_brl": round(random.uniform(120, 190), 2),
                    "pedidos_cancelados": random.randint(0, 5),
                    "tasa_cancelacion_pct": round(random.uniform(0.5, 3.0), 2),
                }
            )

    # Series totales
    total_por_mes = {}
    for r in ing_mensual:
        k = (r["anio"], r["mes"], r["nombre_mes"], r["periodo"])
        total_por_mes.setdefault(k, 0)
        total_por_mes[k] += r["ingresos_brl"]
    total_list = sorted(total_por_mes.items(), key=lambda x: x[0][:2])

    acum = 0
    pts_acum, pts_ped, pts_tick, pts_marg = [], [], [], []
    for (anio, mes, nombre, periodo), v in total_list:
        acum += v
        lbl = f"{['','Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'][mes]} {anio}"
        pts_acum.append(
            {
                "periodo": periodo,
                "anio": anio,
                "mes": mes,
                "nombre_mes": lbl,
                "valor": round(acum, 2),
            }
        )
        pts_ped.append(
            {
                "periodo": periodo,
                "anio": anio,
                "mes": mes,
                "nombre_mes": lbl,
                "valor": float(random.randint(80, 350)),
            }
        )
        pts_tick.append(
            {
                "periodo": periodo,
                "anio": anio,
                "mes": mes,
                "nombre_mes": lbl,
                "valor": round(random.uniform(130, 175), 2),
            }
        )
        pts_marg.append(
            {
                "periodo": periodo,
                "anio": anio,
                "mes": mes,
                "nombre_mes": lbl,
                "valor": round(random.uniform(18, 30), 2),
            }
        )

    return {
        "ingresos_mensuales": ing_mensual,
        "serie_ingresos_acumulados": {
            "nombre": "Acumulado",
            "unidad": "BRL",
            "puntos": pts_acum,
        },
        "serie_pedidos": {"nombre": "Pedidos", "unidad": "unidades", "puntos": pts_ped},
        "serie_ticket_promedio": {
            "nombre": "Ticket",
            "unidad": "BRL",
            "puntos": pts_tick,
        },
        "serie_margen_pct": {"nombre": "Margen %", "unidad": "%", "puntos": pts_marg},
    }


def _fallback_comparativa() -> dict:
    cats = [
        ("Juguetes", "Juguetes", 1520, 187_450, 33_741, 18.0, 29.2, 30.6),
        ("Salud y Belleza", "Salud y Belleza", 420, 62_300, 21_805, 35.0, 8.1, 10.2),
        ("Accesorios Computadora", "Electrónica", 380, 52_700, 11_594, 22.0, 7.3, 8.6),
        (
            "Muebles y Decoración",
            "Hogar y Decoración",
            310,
            48_200,
            13_496,
            28.0,
            6.0,
            7.9,
        ),
        ("Deportes y Ocio", "Deportes y Ocio", 290, 41_600, 12_480, 30.0, 5.6, 6.8),
        ("Moda y Accesorios", "Moda y Accesorios", 250, 38_900, 15_560, 40.0, 4.8, 6.3),
        ("Telefonía", "Electrónica", 230, 35_400, 7_788, 22.0, 4.4, 5.8),
        (
            "Artículos del Hogar",
            "Hogar y Decoración",
            210,
            28_700,
            8_036,
            28.0,
            4.0,
            4.7,
        ),
        ("Electrónica General", "Electrónica", 180, 26_100, 5_742, 22.0, 3.5, 4.3),
        ("Bebé", "Salud y Belleza", 160, 22_400, 7_168, 32.0, 3.1, 3.7),
        ("Relojes y Regalos", "Otras", 140, 19_800, 4_950, 25.0, 2.7, 3.2),
        ("Papelería", "Otras", 120, 14_200, 3_550, 25.0, 2.3, 2.3),
    ]
    total_items = sum(c[2] for c in cats)
    total_ing = sum(c[3] for c in cats)
    categorias = []
    for i, (cat, grupo, itms, ing, cont, marg, pvol, ping) in enumerate(cats, 1):
        categorias.append(
            {
                "categoria": cat,
                "grupo": grupo,
                "total_items": itms,
                "ingresos_brl": ing,
                "contribucion_brl": cont,
                "margen_pct": marg,
                "participacion_vol_pct": round(itms / total_items * 100, 2),
                "participacion_ing_pct": round(ing / total_ing * 100, 2),
                "rank_ingresos": i,
                "rank_margen": i,
            }
        )

    estados = [
        ("SP", "Sudeste", 1820, 294_000, 161.5, 48.1, 11.2),
        ("RJ", "Sudeste", 620, 102_000, 164.5, 16.7, 12.8),
        ("MG", "Sudeste", 510, 84_000, 164.7, 13.7, 13.4),
        ("RS", "Sul", 280, 46_000, 164.3, 7.5, 10.5),
        ("PR", "Sul", 250, 40_000, 160.0, 6.5, 10.8),
        ("SC", "Sul", 180, 29_500, 163.9, 4.8, 11.0),
        ("BA", "Nordeste", 160, 24_000, 150.0, 3.9, 17.2),
        ("GO", "Centro-Oeste", 130, 20_000, 153.8, 3.3, 13.1),
        ("DF", "Centro-Oeste", 110, 18_000, 163.6, 2.9, 12.5),
        ("PE", "Nordeste", 100, 16_000, 160.0, 2.6, 16.8),
    ]
    total_ing_est = sum(e[3] for e in estados)
    estados_l = []
    for est, reg, nped, ing, tick, _, te in estados:
        estados_l.append(
            {
                "estado": est,
                "region": reg,
                "num_pedidos": nped,
                "ingresos_brl": ing,
                "ticket_promedio_brl": tick,
                "participacion_pct": round(ing / total_ing_est * 100, 2),
                "tiempo_entrega_prom": te,
            }
        )

    pagos = [
        ("credit_card", "Tarjeta de Crédito", 2991, 461_500, 154.3),
        ("boleto", "Boleto Bancário", 598, 92_000, 153.8),
        ("voucher", "Vale Descuento", 279, 43_000, 154.1),
        ("debit_card", "Tarjeta de Débito", 119, 18_500, 155.5),
    ]
    total_ped = sum(p[2] for p in pagos)
    total_monto = sum(p[3] for p in pagos)
    pagos_l = []
    for pt, desc, nped, monto, ticket in pagos:
        pagos_l.append(
            {
                "metodo": pt,
                "descripcion": desc,
                "num_pedidos": nped,
                "monto_total_brl": monto,
                "ticket_promedio_brl": ticket,
                "participacion_frecuencia_pct": round(nped / total_ped * 100, 2),
                "participacion_monto_pct": round(monto / total_monto * 100, 2),
            }
        )

    return {"categorias": categorias, "estados": estados_l, "metodos_pago": pagos_l}


def _fallback_semaforizados() -> dict:
    import random

    random.seed(11)
    meses = [(2017, m) for m in range(1, 13)] + [(2018, m) for m in range(1, 10)]
    meses_n = [
        "",
        "Ene",
        "Feb",
        "Mar",
        "Abr",
        "May",
        "Jun",
        "Jul",
        "Ago",
        "Sep",
        "Oct",
        "Nov",
        "Dic",
    ]

    # Datos reales Olist: ingresos mes promedio ~ R$1.27M, ticket ~R$341, cancel 0.46%, entrega 12d
    ing_reales_mes = [
        400_000, 520_000, 680_000, 810_000, 950_000, 1_040_000,
        1_120_000, 1_210_000, 1_300_000, 1_380_000, 1_450_000, 1_520_000,
        1_600_000, 1_680_000, 1_740_000, 1_800_000, 1_860_000, 1_920_000,
        1_950_000, 1_970_000, 1_980_000,
    ]
    tick_reales_mes = [
        310, 322, 330, 335, 338, 340, 342, 341, 343, 345, 341, 339,
        342, 345, 341, 338, 340, 343, 344, 342, 340,
    ]
    cancel_reales = [
        0.52, 0.48, 0.45, 0.44, 0.47, 0.46, 0.43, 0.45, 0.46, 0.44, 0.43, 0.46,
        0.45, 0.44, 0.46, 0.45, 0.43, 0.44, 0.46, 0.45, 0.44,
    ]

    ing_hist, tick_hist, can_hist = [], [], []
    for i, (a, m) in enumerate(meses):
        lbl = f"{meses_n[m]} {a}"
        p   = f"{a}-{m:02d}"
        v_i = ing_reales_mes[i] if i < len(ing_reales_mes) else 1_200_000
        v_t = tick_reales_mes[i] if i < len(tick_reales_mes) else 340
        v_c = cancel_reales[i] if i < len(cancel_reales) else 0.46
        ing_hist .append({"periodo":p,"anio":a,"mes":m,"nombre_mes":lbl,"valor":v_i})
        tick_hist.append({"periodo":p,"anio":a,"mes":m,"nombre_mes":lbl,"valor":v_t})
        can_hist .append({"periodo":p,"anio":a,"mes":m,"nombre_mes":lbl,"valor":v_c})

    semaforos = [
        {
            "kpi_id":"KPI-1",
            "nombre": "Valor Total Pagado (mensual)",
            "valor_actual": 1_268_661.37,   # 30.4M / 24 meses
            "unidad":"BRL",
            "meta_verde": 1_500_000,
            "meta_amarilla": 800_000,
            "color": "yellow",              # 1.27M < 1.5M → alerta
            "descripcion_meta": "Meta: > R$ 1.5M/mes",
            "formula": "SUM(payment_value) / N meses",
            "variacion_pct": 8.3,
            "historico": ing_hist,
        },
        {
            "kpi_id":"KPI-5",
            "nombre": "Ticket Promedio por Pedido",
            "valor_actual": 340.87,         # 30.4M / 89,316 pedidos
            "unidad":"BRL",
            "meta_verde": 300,
            "meta_amarilla": 200,
            "color": "green",               # 341 > 300 → óptimo
            "descripcion_meta": "Meta: > R$ 300/pedido",
            "formula": "SUM(payment_value) / COUNT(DISTINCT order_id)",
            "variacion_pct": -2.1,
            "historico": tick_hist,
        },
        {
            "kpi_id":"KPI-6",
            "nombre": "Tasa de Cancelación",
            "valor_actual": 0.46,           # dato real del dataset
            "unidad":"%",
            "meta_verde": 0.5,
            "meta_amarilla": 1.5,
            "color": "green",               # 0.46% ≤ 0.5% → óptimo
            "descripcion_meta": "Meta: < 0.5% (menor = mejor)",
            "formula": "N° cancelados / Total × 100",
            "variacion_pct": -0.04,
            "historico": can_hist,
        },
        {
            "kpi_id":"KPI-10",
            "nombre": "Tiempo Promedio de Entrega",
            "valor_actual": 12.0,           # dato real: 12 días promedio
            "unidad":"días",
            "meta_verde": 10,
            "meta_amarilla": 15,
            "color": "yellow",              # 12 > 10 → alerta
            "descripcion_meta": "Meta: < 10 días (menor = mejor)",
            "formula": "AVG(tiempo_entrega_dias) WHERE flag_entrega_valida=1",
            "variacion_pct": -1.5,
            "historico": [],
        },
    ]
    return {
        "semaforos": semaforos,
        "resumen_colores": {"green": 2, "yellow": 2, "red": 0},
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port  = int(os.getenv("PORT", os.getenv("DASHBOARD_PORT", 8050)))
    debug = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
    print(f"\n{'='*50}")
    print(f"  Olist BI Dashboard")
    print(f"  Abre en tu navegador: http://localhost:{port}")
    print(f"{'='*50}\n")
    app.run(debug=debug, host="127.0.0.1", port=port)
