from fastapi import APIRouter
from backend.hive_conn import hive_query, is_hive_available, TBL
from backend.schemas import OpcionesFiltros
from datetime import date

router = APIRouter(prefix="/api/v1/filtros", tags=["Filtros 9.5"])


@router.get("/opciones", response_model=OpcionesFiltros,
            summary="Opciones de filtros (9.5)")
def get_opciones_filtros():
    """Devuelve las opciones disponibles para los filtros del dashboard."""
    if not is_hive_available():
        return OpcionesFiltros(
            regiones=["Sudeste", "Sul", "Centro-Oeste", "Nordeste", "Norte"],
            estados=["SP","RJ","MG","RS","PR","SC","BA","GO","ES","PE",
                     "CE","DF","AM","PA","RO","AC","AP","RR","TO","MA",
                     "PB","RN","AL","SE","PI","MT","MS"],
            categorias=["Juguetes","Salud y Belleza","Accesorios de Computadora",
                        "Muebles y Decoración","Deportes y Ocio","Moda y Accesorios",
                        "Telefonía","Artículos del Hogar","Electrónica General",
                        "Bebé","Relojes y Regalos","Papelería","Herramientas de Jardín",
                        "Automotriz","Cama, Baño y Mesa","Perfumería","Libros"],
            grupos_categoria=["Juguetes","Electrónica","Salud y Belleza",
                              "Hogar y Decoración","Deportes y Ocio","Moda y Accesorios","Otras"],
            metodos_pago=["credit_card","boleto","voucher","debit_card"],
            fecha_min=date(2016, 9, 1),
            fecha_max=date(2018, 9, 30),
            anios=[2016, 2017, 2018],
        )

    df_reg  = hive_query(f"SELECT DISTINCT region_brasil FROM {TBL['dim_geografia']} ORDER BY region_brasil")
    df_est  = hive_query(f"SELECT DISTINCT customer_state FROM {TBL['dim_geografia']} ORDER BY customer_state")
    df_cat  = hive_query(f"SELECT DISTINCT category_name_es FROM {TBL['dim_producto']} ORDER BY category_name_es")
    df_grp  = hive_query(f"SELECT DISTINCT category_group FROM {TBL['dim_producto']} ORDER BY category_group")
    df_pago = hive_query(f"SELECT DISTINCT payment_type FROM {TBL['fact_payment']}")
    df_dt   = hive_query(f"SELECT MIN(fecha) AS fmin, MAX(fecha) AS fmax FROM {TBL['dim_tiempo']}")
    df_yr   = hive_query(f"SELECT DISTINCT anio FROM {TBL['dim_tiempo']} ORDER BY anio")

    fmin = date(2016, 9, 1)
    fmax = date(2018, 9, 30)
    try:
        fmin = date.fromisoformat(str(df_dt.iloc[0]["fmin"])[:10])
        fmax = date.fromisoformat(str(df_dt.iloc[0]["fmax"])[:10])
    except Exception:
        pass

    return OpcionesFiltros(
        regiones  =df_reg["region_brasil"].dropna().tolist(),
        estados   =df_est["customer_state"].dropna().tolist(),
        categorias=df_cat["category_name_es"].dropna().tolist(),
        grupos_categoria=df_grp["category_group"].dropna().tolist(),
        metodos_pago=df_pago["payment_type"].dropna().tolist(),
        fecha_min=fmin,
        fecha_max=fmax,
        anios=df_yr["anio"].dropna().astype(int).tolist(),
    )
