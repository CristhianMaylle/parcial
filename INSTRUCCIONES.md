# Olist BI Dashboard — Capítulo 9

## SI807U · Sistemas de Inteligencia de Negocios

---

## Arquitectura

```
parcial/
├── backend/               ← FastAPI + SQLAlchemy + PostgreSQL
│   ├── main.py            ← App FastAPI (contrato de API)
│   ├── models.py          ← ORM: esquema estrella (FACT + DIM)
│   ├── schemas.py         ← Pydantic schemas (CONTRATO API)
│   ├── database.py        ← Conexión a PostgreSQL
│   ├── seed.py            ← Generador de datos simulados
│   └── routers/
│       ├── kpis.py        ← Endpoints 9.1–9.4
│       └── filtros.py     ← Endpoint 9.5
├── dashboard/
│   ├── app.py             ← Dashboard Dash (UI completa)
│   ├── api_client.py      ← Cliente HTTP → backend
│   ├── layouts/
│   │   └── charts.py      ← Fábrica de gráficos Plotly
│   └── assets/
│       └── style.css      ← Tema futurista
├── docker-compose.yml     ← PostgreSQL
├── .env                   ← Variables de entorno
└── setup.py               ← Script de instalación
```

---

## Inicio rápido

### Opción A — Solo dashboard (sin base de datos)

El dashboard funciona con datos simulados de fallback:

```bash
pip install -r requirements.txt
python dashboard/app.py
# Abre: http://localhost:8050
```

### Opción B — Con PostgreSQL real (datos simulados)

```bash
# 1. Levantar PostgreSQL
docker compose up -d postgres

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Cargar datos simulados (~4000 pedidos Olist-like)
python -m backend.seed

# 4. Iniciar API (terminal 1)
python -m uvicorn backend.main:app --reload --port 8000

# 5. Iniciar dashboard (terminal 2)
python dashboard/app.py
```

### Opción C — Despliegue en Render (dashboard público)

Configura un servicio web Python en Render con estas opciones:

- Build command: `pip install -r requirements.txt`
- Start command: `python dashboard/app.py`

Render provee la variable de entorno `PORT`, y la app ya la usa correctamente.
Con esta configuración, el dashboard se ejecuta públicamente con datos simulados sin necesidad de backend.

---

## Endpoints del API (Contrato de Backend)

| Método | Ruta                             | Sección | Descripción                |
| ------ | -------------------------------- | ------- | -------------------------- |
| GET    | `/api/v1/kpis/resumen-ejecutivo` | 9.1     | KPIs + top clientes        |
| GET    | `/api/v1/kpis/acumulativas`      | 9.2     | Series temporales          |
| GET    | `/api/v1/kpis/comparativa`       | 9.3     | Categorías, estados, pagos |
| GET    | `/api/v1/kpis/semaforizados`     | 9.4     | KPIs con semáforo          |
| GET    | `/api/v1/filtros/opciones`       | 9.5     | Opciones de filtros        |

Todos los endpoints aceptan parámetros de filtro:
`fecha_inicio`, `fecha_fin`, `region`, `estado`, `categoria`, `metodo_pago`

Documentación interactiva: `http://localhost:8000/docs`

---

## Conexión DBeaver → PostgreSQL

| Campo         | Valor                                       |
| ------------- | ------------------------------------------- |
| Host          | localhost                                   |
| Puerto        | 5432                                        |
| Base de datos | olist_bi                                    |
| Usuario       | olist                                       |
| Contraseña    | olist123                                    |
| Driver        | PostgreSQL                                  |
| JDBC URL      | `jdbc:postgresql://localhost:5432/olist_bi` |

---

## KPIs del Dashboard

| KPI    | Nombre                    | Semáforo           |
| ------ | ------------------------- | ------------------ |
| KPI-1  | Ingresos Totales          | Verde ≥ R$500K/mes |
| KPI-2  | Cantidad Ítems Vendidos   | Informativo        |
| KPI-3  | Ingresos por Categoría    | Comparativo        |
| KPI-4  | Ingresos por Estado       | Comparativo        |
| KPI-5  | Contribución Estimada     | Comparativo        |
| KPI-6  | Margen %                  | Meta ≥ 25%         |
| KPI-7  | Ticket Promedio           | Verde ≥ R$160      |
| KPI-8  | Distribución Métodos Pago | Comparativo        |
| KPI-9  | Tasa Cancelación          | Verde < 1.5%       |
| KPI-10 | Tiempo Prom. Entrega      | Verde < 10 días    |

---

## Para conectar con datos reales (Hive/DBeaver)

Modifica `DATABASE_URL` en `.env`:

```
# Para Hive via HiveServer2 (requiere driver adicional):
# DATABASE_URL=hive://hive:hive@sandbox-hdp.hortonworks.com:10000/ecommerce

# Para PostgreSQL (producción):
DATABASE_URL=postgresql://usuario:contraseña@host:5432/base_datos
```

Los queries del backend (`backend/routers/kpis.py`) están escritos en
SQLAlchemy ORM — son independientes del motor de base de datos subyacente.
