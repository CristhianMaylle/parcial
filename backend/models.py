from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, SmallInteger
from backend.database import Base


class DimTiempo(Base):
    __tablename__ = "dim_tiempo"
    sk_tiempo = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    anio = Column(Integer)
    trimestre = Column(Integer)
    mes = Column(Integer)
    nombre_mes = Column(String(20))
    semana_anio = Column(Integer)
    dia_semana = Column(Integer)
    inicio_mes = Column(Date)
    fin_mes = Column(Date)
    es_fin_semana = Column(SmallInteger, default=0)


class DimCliente(Base):
    __tablename__ = "dim_cliente"
    sk_cliente = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String(50))
    customer_zip_prefix = Column(String(10))
    customer_city = Column(String(100))
    customer_state = Column(String(2))
    region_brasil = Column(String(50))


class DimProducto(Base):
    __tablename__ = "dim_producto"
    sk_producto = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(50))
    product_category_name = Column(String(100))
    category_name_es = Column(String(100))
    category_group = Column(String(50))
    estimated_cost = Column(Float)
    estimated_margin_pct = Column(Float)


class DimSeller(Base):
    __tablename__ = "dim_seller"
    sk_seller = Column(Integer, primary_key=True, index=True)
    seller_id = Column(String(50))
    seller_city = Column(String(100))
    seller_state = Column(String(2))
    region_brasil = Column(String(50))


class DimTipoPago(Base):
    __tablename__ = "dim_tipo_pago"
    sk_pago = Column(Integer, primary_key=True, index=True)
    payment_type = Column(String(50))
    payment_type_desc = Column(String(100))
    es_diferido = Column(SmallInteger, default=0)


class DimPedido(Base):
    __tablename__ = "dim_pedido"
    sk_pedido = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50))
    order_status = Column(String(30))
    flag_cancelado = Column(SmallInteger, default=0)
    flag_entregado = Column(SmallInteger, default=0)
    flag_entrega_valida = Column(SmallInteger, default=0)
    purchase_ts = Column(DateTime)
    approved_ts = Column(DateTime)
    delivered_ts = Column(DateTime, nullable=True)
    estimated_delivery_dt = Column(Date, nullable=True)
    tiempo_entrega_dias = Column(Integer, nullable=True)
    adelanto_retraso_dias = Column(Integer, nullable=True)


class FactSalesItem(Base):
    __tablename__ = "fact_sales_item"
    sk_venta = Column(Integer, primary_key=True, index=True)
    sk_pedido = Column(Integer, ForeignKey("dim_pedido.sk_pedido"))
    sk_cliente = Column(Integer, ForeignKey("dim_cliente.sk_cliente"))
    sk_producto = Column(Integer, ForeignKey("dim_producto.sk_producto"))
    sk_seller = Column(Integer, ForeignKey("dim_seller.sk_seller"))
    sk_pago = Column(Integer, ForeignKey("dim_tipo_pago.sk_pago"))
    sk_tiempo = Column(Integer, ForeignKey("dim_tiempo.sk_tiempo"))
    num_secuencia = Column(Integer, default=1)
    precio_item = Column(Float)
    flete_item = Column(Float)
    costo_estimado_item = Column(Float)
    contribucion_estimada = Column(Float)
    margen_pct_estimado = Column(Float)
    cantidad_items = Column(Integer, default=1)
    ventas_netas_asignadas = Column(Float)
    tiempo_entrega_dias = Column(Integer, nullable=True)
    flag_cancelado = Column(SmallInteger, default=0)
    flag_entrega_valida = Column(SmallInteger, default=0)


class FactPaymentOrder(Base):
    __tablename__ = "fact_payment_order"
    sk_pago_pedido = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50))
    sk_pedido = Column(Integer, ForeignKey("dim_pedido.sk_pedido"))
    sk_cliente = Column(Integer, ForeignKey("dim_cliente.sk_cliente"))
    sk_tiempo = Column(Integer, ForeignKey("dim_tiempo.sk_tiempo"))
    sk_tipo_pago = Column(Integer, ForeignKey("dim_tipo_pago.sk_pago"))
    pago_total_pedido = Column(Float)
    num_cuotas = Column(Integer, default=1)
    ticket_promedio_pedido = Column(Float)
    pago_credito = Column(Float, default=0)
    pago_boleto = Column(Float, default=0)
    pago_voucher = Column(Float, default=0)
    pago_debito = Column(Float, default=0)
    flag_cancelado = Column(SmallInteger, default=0)
