"""
Generador de datos simulados para Olist BI — PostgreSQL
Refleja las distribuciones reales del dataset público (Kaggle, 2018).
Ejecutar: python -m backend.seed
"""
import uuid, random, os
from datetime import datetime, timedelta, date
from calendar import monthrange

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

# Importar después de load_dotenv para que DATABASE_URL esté disponible
from backend.database import engine, SessionLocal, Base
from backend import models

random.seed(42)
np.random.seed(42)

# ─── Constantes de dominio ─────────────────────────────────────────────────────

ESTADOS_REGION = {
    "SP": "Sudeste", "RJ": "Sudeste", "MG": "Sudeste", "ES": "Sudeste",
    "RS": "Sul",     "PR": "Sul",     "SC": "Sul",
    "BA": "Nordeste","PE": "Nordeste","CE": "Nordeste","MA": "Nordeste",
    "PB": "Nordeste","RN": "Nordeste","AL": "Nordeste","SE": "Nordeste","PI": "Nordeste",
    "GO": "Centro-Oeste","MT": "Centro-Oeste","MS": "Centro-Oeste","DF": "Centro-Oeste",
    "AM": "Norte","PA": "Norte","RO": "Norte","AC": "Norte","AP": "Norte","RR": "Norte","TO": "Norte",
}

ESTADO_PESOS = {
    "SP": 0.40, "RJ": 0.12, "MG": 0.10, "RS": 0.06, "PR": 0.06,
    "SC": 0.04, "BA": 0.04, "GO": 0.02, "ES": 0.02, "PE": 0.02,
    "CE": 0.02, "DF": 0.02,
}
_otros = [e for e in ESTADOS_REGION if e not in ESTADO_PESOS]
for _e in _otros:
    ESTADO_PESOS[_e] = 0.005
_total = sum(ESTADO_PESOS.values())
ESTADO_PESOS = {k: v / _total for k, v in ESTADO_PESOS.items()}

CIUDADES_ESTADO = {
    "SP": ["São Paulo","Campinas","Santos","Guarulhos"],
    "RJ": ["Rio de Janeiro","Niterói","Nova Iguaçu"],
    "MG": ["Belo Horizonte","Uberlândia","Contagem"],
    "RS": ["Porto Alegre","Caxias do Sul","Pelotas"],
    "PR": ["Curitiba","Londrina","Maringá"],
    "SC": ["Florianópolis","Joinville","Blumenau"],
    "BA": ["Salvador","Feira de Santana","Vitória da Conquista"],
    "GO": ["Goiânia","Aparecida de Goiânia"],
    "ES": ["Vitória","Vila Velha"],
    "PE": ["Recife","Caruaru"],
    "CE": ["Fortaleza","Caucaia"],
    "DF": ["Brasília"],
    "AM": ["Manaus"],"PA": ["Belém"],"RO": ["Porto Velho"],"AC": ["Rio Branco"],
    "AP": ["Macapá"],"RR": ["Boa Vista"],"TO": ["Palmas"],
    "MA": ["São Luís"],"PB": ["João Pessoa"],"RN": ["Natal"],
    "AL": ["Maceió"],"SE": ["Aracaju"],"PI": ["Teresina"],
    "MT": ["Cuiabá"],"MS": ["Campo Grande"],
}

CATEGORIAS = {
    "toys":                         ("Juguetes",                   "Juguetes",           18.0),
    "computers_accessories":        ("Accesorios de Computadora",  "Electrónica",        22.0),
    "health_beauty":                ("Salud y Belleza",            "Salud y Belleza",    35.0),
    "furniture_decor":              ("Muebles y Decoración",       "Hogar y Decoración", 28.0),
    "sports_leisure":               ("Deportes y Ocio",            "Deportes y Ocio",    30.0),
    "fashion_bags_accessories":     ("Moda y Accesorios",          "Moda y Accesorios",  40.0),
    "telephony":                    ("Telefonía",                  "Electrónica",        22.0),
    "housewares":                   ("Artículos del Hogar",        "Hogar y Decoración", 28.0),
    "electronics":                  ("Electrónica General",        "Electrónica",        22.0),
    "baby":                         ("Bebé",                       "Salud y Belleza",    32.0),
    "watches_gifts":                ("Relojes y Regalos",          "Otras",              25.0),
    "stationery":                   ("Papelería",                  "Otras",              25.0),
    "garden_tools":                 ("Herramientas de Jardín",     "Hogar y Decoración", 28.0),
    "auto":                         ("Automotriz",                 "Otras",              25.0),
    "bed_bath_table":               ("Cama, Baño y Mesa",          "Hogar y Decoración", 28.0),
    "perfumery":                    ("Perfumería",                 "Salud y Belleza",    35.0),
    "cool_stuff":                   ("Artículos Especiales",       "Otras",              25.0),
    "books_general_interest":       ("Libros",                     "Otras",              25.0),
    "office_furniture":             ("Muebles de Oficina",         "Hogar y Decoración", 28.0),
    "construction_tools_lights":    ("Herramientas Construcción",  "Hogar y Decoración", 25.0),
}

CAT_PESOS = {
    "toys": 0.30,
    "health_beauty": 0.08,
    "computers_accessories": 0.07,
    "furniture_decor": 0.06,
    "sports_leisure": 0.06,
    "fashion_bags_accessories": 0.05,
    "telephony": 0.05,
    "housewares": 0.04,
    "electronics": 0.04,
    "baby": 0.03,
}
_otras_cats = [c for c in CATEGORIAS if c not in CAT_PESOS]
for _c in _otras_cats:
    CAT_PESOS[_c] = 0.01
_total_c = sum(CAT_PESOS.values())
CAT_PESOS = {k: v / _total_c for k, v in CAT_PESOS.items()}

PAGOS = [
    ("credit_card", "Tarjeta de Crédito", 1, 0.75),
    ("boleto",      "Boleto Bancário",    0, 0.15),
    ("voucher",     "Vale Descuento",     1, 0.07),
    ("debit_card",  "Tarjeta de Débito",  0, 0.03),
]

PRECIO_POR_CAT = {
    "toys": (30, 200), "computers_accessories": (50, 400),
    "health_beauty": (20, 150), "furniture_decor": (100, 800),
    "sports_leisure": (30, 300), "fashion_bags_accessories": (40, 300),
    "telephony": (100, 500), "housewares": (20, 200),
    "electronics": (50, 600), "baby": (20, 200),
    "watches_gifts": (50, 500), "stationery": (10, 80),
    "garden_tools": (30, 250), "auto": (30, 400),
    "bed_bath_table": (40, 350), "perfumery": (30, 200),
    "cool_stuff": (30, 300), "books_general_interest": (10, 60),
    "office_furniture": (100, 600), "construction_tools_lights": (30, 400),
}

FECHA_INICIO = date(2017, 1, 1)
FECHA_FIN    = date(2018, 9, 30)
N_CLIENTES   = 600
N_PRODUCTOS  = 200
N_SELLERS    = 60
N_PEDIDOS    = 4000


# ─── Helpers ──────────────────────────────────────────────────────────────────

def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def rand_datetime(start: date, end: date) -> datetime:
    d = rand_date(start, end)
    h = random.randint(6, 22)
    m = random.randint(0, 59)
    return datetime(d.year, d.month, d.day, h, m)


# ─── Generadores ──────────────────────────────────────────────────────────────

def gen_dim_tiempo(db: Session):
    """Genera dimensión de tiempo para todo el rango del proyecto."""
    current = FECHA_INICIO
    sk = 1
    while current <= FECHA_FIN:
        _, last_day = monthrange(current.year, current.month)
        inicio_mes = date(current.year, current.month, 1)
        fin_mes    = date(current.year, current.month, last_day)
        rec = models.DimTiempo(
            sk_tiempo    = sk,
            fecha        = current,
            anio         = current.year,
            trimestre    = (current.month - 1) // 3 + 1,
            mes          = current.month,
            nombre_mes   = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                            "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"][current.month - 1],
            semana_anio  = current.isocalendar()[1],
            dia_semana   = current.isoweekday(),
            inicio_mes   = inicio_mes,
            fin_mes      = fin_mes,
            es_fin_semana= 1 if current.isoweekday() >= 6 else 0,
        )
        db.add(rec)
        current += timedelta(days=1)
        sk += 1
    db.commit()
    print(f"  dim_tiempo: {sk-1} filas")


def gen_dim_cliente(db: Session) -> list[int]:
    estados = list(ESTADO_PESOS.keys())
    pesos   = list(ESTADO_PESOS.values())
    sks = []
    for sk in range(1, N_CLIENTES + 1):
        estado = random.choices(estados, weights=pesos)[0]
        ciudad = random.choice(CIUDADES_ESTADO.get(estado, [estado]))
        rec = models.DimCliente(
            sk_cliente       = sk,
            customer_id      = str(uuid.uuid4())[:20],
            customer_zip_prefix = f"{random.randint(10000, 99999)}",
            customer_city    = ciudad,
            customer_state   = estado,
            region_brasil    = ESTADOS_REGION[estado],
        )
        db.add(rec)
        sks.append(sk)
    db.commit()
    print(f"  dim_cliente: {N_CLIENTES} filas")
    return sks


def gen_dim_producto(db: Session) -> list[int]:
    cats = list(CATEGORIAS.keys())
    sks = []
    for sk in range(1, N_PRODUCTOS + 1):
        cat_key = random.choices(cats, weights=[CAT_PESOS[c] for c in cats])[0]
        nombre_es, grupo, margen_pct = CATEGORIAS[cat_key]
        precio_rango = PRECIO_POR_CAT[cat_key]
        precio_ref   = random.uniform(*precio_rango)
        costo_est    = precio_ref * (1 - margen_pct / 100)
        rec = models.DimProducto(
            sk_producto           = sk,
            product_id            = str(uuid.uuid4())[:20],
            product_category_name = cat_key,
            category_name_es      = nombre_es,
            category_group        = grupo,
            estimated_cost        = round(costo_est, 2),
            estimated_margin_pct  = margen_pct,
        )
        db.add(rec)
        sks.append(sk)
    db.commit()
    print(f"  dim_producto: {N_PRODUCTOS} filas")
    return sks


def gen_dim_seller(db: Session) -> list[int]:
    estados = list(ESTADOS_REGION.keys())
    sks = []
    for sk in range(1, N_SELLERS + 1):
        estado = random.choice(estados)
        ciudad = random.choice(CIUDADES_ESTADO.get(estado, [estado]))
        rec = models.DimSeller(
            sk_seller    = sk,
            seller_id    = str(uuid.uuid4())[:20],
            seller_city  = ciudad,
            seller_state = estado,
            region_brasil= ESTADOS_REGION[estado],
        )
        db.add(rec)
        sks.append(sk)
    db.commit()
    print(f"  dim_seller: {N_SELLERS} filas")
    return sks


def gen_dim_tipo_pago(db: Session) -> dict:
    sk_map = {}
    for sk, (ptype, desc, diferido, _) in enumerate(PAGOS, 1):
        rec = models.DimTipoPago(
            sk_pago          = sk,
            payment_type     = ptype,
            payment_type_desc= desc,
            es_diferido      = diferido,
        )
        db.add(rec)
        sk_map[ptype] = sk
    db.commit()
    print(f"  dim_tipo_pago: {len(PAGOS)} filas")
    return sk_map


def _sk_tiempo_para_fecha(fecha: date, db: Session) -> int:
    row = db.query(models.DimTiempo).filter(models.DimTiempo.fecha == fecha).first()
    return row.sk_tiempo if row else 1


def gen_pedidos_y_facts(
    db: Session,
    sks_cliente: list[int],
    sks_producto: list[int],
    sks_seller: list[int],
    sk_pago_map: dict,
):
    pago_tipos  = [p[0] for p in PAGOS]
    pago_pesos  = [p[3] for p in PAGOS]

    # Precargar todos los sk_tiempo en memoria para evitar N+1 queries
    tiempos = db.query(models.DimTiempo).all()
    fecha_a_sk = {t.fecha: t.sk_tiempo for t in tiempos}

    # Precargar productos
    productos_map = {p.sk_producto: p for p in db.query(models.DimProducto).all()}

    pedido_sk  = 1
    venta_sk   = 1
    pago_ped_sk= 1

    # Tendencia mensual de ingresos (crecimiento natural 2017 → 2018)
    for _ in range(N_PEDIDOS):
        # fecha con sesgo hacia meses más recientes (crecimiento)
        dias_total = (FECHA_FIN - FECHA_INICIO).days
        dia_offset = int(np.random.triangular(0, dias_total * 0.6, dias_total))
        purchase_date = FECHA_INICIO + timedelta(days=min(dia_offset, dias_total))
        purchase_ts   = datetime(purchase_date.year, purchase_date.month, purchase_date.day,
                                 random.randint(7, 22), random.randint(0, 59))

        sk_cliente  = random.choice(sks_cliente)
        sk_pago_tipo= random.choices(pago_tipos, weights=pago_pesos)[0]

        # Tiempo de entrega (distribución realista por región)
        cliente_obj = db.query(models.DimCliente).filter(
            models.DimCliente.sk_cliente == sk_cliente
        ).first()
        region = cliente_obj.region_brasil if cliente_obj else "Sudeste"
        entrega_medias = {
            "Sudeste": 8, "Sul": 10, "Centro-Oeste": 12,
            "Nordeste": 16, "Norte": 20,
        }
        tiempo_entrega = max(1, int(np.random.normal(entrega_medias.get(region, 12), 3)))

        # Estado del pedido (98% entregado, 2% cancelado)
        es_cancelado = 1 if random.random() < 0.02 else 0
        delivered_ts = (purchase_ts + timedelta(days=tiempo_entrega)) if not es_cancelado else None
        estimated_dt = (purchase_ts + timedelta(days=tiempo_entrega + random.randint(-3, 5))).date() if not es_cancelado else None

        adelanto = None
        if delivered_ts and estimated_dt:
            adelanto = (estimated_dt - delivered_ts.date()).days

        # Crear DimPedido
        pedido = models.DimPedido(
            sk_pedido           = pedido_sk,
            order_id            = str(uuid.uuid4())[:20],
            order_status        = "canceled" if es_cancelado else "delivered",
            flag_cancelado      = es_cancelado,
            flag_entregado      = 0 if es_cancelado else 1,
            flag_entrega_valida = 0 if es_cancelado else 1,
            purchase_ts         = purchase_ts,
            approved_ts         = purchase_ts + timedelta(hours=random.randint(1, 24)),
            delivered_ts        = delivered_ts,
            estimated_delivery_dt = estimated_dt,
            tiempo_entrega_dias = tiempo_entrega if not es_cancelado else None,
            adelanto_retraso_dias = adelanto,
        )
        db.add(pedido)

        sk_tiempo = fecha_a_sk.get(purchase_date, 1)

        # Items por pedido (1–3 ítems)
        num_items = random.choices([1, 2, 3], weights=[0.65, 0.25, 0.10])[0]
        total_precio = 0.0
        items_info = []
        for seq in range(1, num_items + 1):
            sk_prod = random.choice(sks_producto)
            prod    = productos_map[sk_prod]
            cat_key = prod.product_category_name
            precio  = round(random.uniform(*PRECIO_POR_CAT.get(cat_key, (30, 200))), 2)
            flete   = round(random.uniform(5, 50), 2)
            costo_est = round(precio * (1 - prod.estimated_margin_pct / 100), 2)
            contrib  = round(precio - costo_est - flete, 2)
            margen_pct = round((contrib / precio * 100) if precio > 0 else 0, 2)
            total_precio += precio

            item = models.FactSalesItem(
                sk_venta             = venta_sk,
                sk_pedido            = pedido_sk,
                sk_cliente           = sk_cliente,
                sk_producto          = sk_prod,
                sk_seller            = random.choice(sks_seller),
                sk_pago              = sk_pago_map[sk_pago_tipo],
                sk_tiempo            = sk_tiempo,
                num_secuencia        = seq,
                precio_item          = precio,
                flete_item           = flete,
                costo_estimado_item  = costo_est,
                contribucion_estimada= contrib,
                margen_pct_estimado  = margen_pct,
                cantidad_items       = 1,
                ventas_netas_asignadas = precio,  # se ajusta después
                tiempo_entrega_dias  = tiempo_entrega if not es_cancelado else None,
                flag_cancelado       = es_cancelado,
                flag_entrega_valida  = 0 if es_cancelado else 1,
            )
            db.add(item)
            items_info.append((venta_sk, precio))
            venta_sk += 1

        # Pago por método
        pago_total = round(total_precio * random.uniform(0.95, 1.10), 2)  # pequeña variación
        pago_cred = pago_total if sk_pago_tipo == "credit_card" else 0.0
        pago_bol  = pago_total if sk_pago_tipo == "boleto" else 0.0
        pago_vou  = pago_total if sk_pago_tipo == "voucher" else 0.0
        pago_deb  = pago_total if sk_pago_tipo == "debit_card" else 0.0

        # FactPaymentOrder
        pago_order = models.FactPaymentOrder(
            sk_pago_pedido      = pago_ped_sk,
            order_id            = pedido.order_id,
            sk_pedido           = pedido_sk,
            sk_cliente          = sk_cliente,
            sk_tiempo           = sk_tiempo,
            sk_tipo_pago        = sk_pago_map[sk_pago_tipo],
            pago_total_pedido   = pago_total,
            num_cuotas          = random.randint(1, 6) if sk_pago_tipo == "credit_card" else 1,
            ticket_promedio_pedido = pago_total,
            pago_credito        = pago_cred,
            pago_boleto         = pago_bol,
            pago_voucher        = pago_vou,
            pago_debito         = pago_deb,
            flag_cancelado      = es_cancelado,
        )
        db.add(pago_order)

        pedido_sk   += 1
        pago_ped_sk += 1

        if pedido_sk % 500 == 0:
            db.commit()
            print(f"    … {pedido_sk} pedidos generados")

    db.commit()
    print(f"  dim_pedido: {pedido_sk-1} | fact_sales_item: {venta_sk-1} | fact_payment_order: {pago_ped_sk-1}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def seed():
    print("Creando tablas …")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Sembrando dimensiones …")
        gen_dim_tiempo(db)
        sks_cli  = gen_dim_cliente(db)
        sks_prod = gen_dim_producto(db)
        sks_sell = gen_dim_seller(db)
        sk_pago  = gen_dim_tipo_pago(db)

        print("Sembrando hechos …")
        gen_pedidos_y_facts(db, sks_cli, sks_prod, sks_sell, sk_pago)
        print("¡Seed completado!")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
