# Olist BI Dashboard

Proyecto de BI para el curso de Sistemas de Inteligencia de Negocios.
El repositorio contiene un backend en FastAPI y un dashboard en Dash que consume los datos de la API.

## Estructura principal

- `backend/` — API REST con FastAPI, SQLAlchemy y data seed.
- `dashboard/` — Aplicación Dash para visualización interactiva.
- `docker-compose.yml` — Levanta PostgreSQL en Docker.
- `requirements.txt` — Dependencias del proyecto.
- `setup.py` — Script de instalación y arranque asistido.
- `.env` — Variables de entorno usadas por el dashboard y el backend.

## Funcionalidad

- Dashboard interactivo con KPIs, semáforos y gráficos comparativos.
- Backend con endpoints API para:
  - resumen ejecutivo
  - series acumulativas
  - comparativas por categoría y estado
  - semaforización de KPIs
  - filtros dinámicos
- Soporta ejecuciones con datos simulados o con PostgreSQL real.

## Ejecución rápida

### Opción A — Solo dashboard (con datos simulados)

```bash
pip install -r requirements.txt
python dashboard/app.py
```

Luego abre:

- Dashboard: `http://localhost:8050`
- API docs: `http://localhost:8000/docs`

### Opción B — Con PostgreSQL real

```bash
# 1. Levantar PostgreSQL
docker compose up -d postgres

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Cargar datos simulados
python -m backend.seed

# 4. Iniciar backend
python -m uvicorn backend.main:app --reload --port 8000

# 5. Iniciar dashboard
python dashboard/app.py
```

## Variables de entorno

El proyecto usa `.env` para configuración de conexión y variables del dashboard.
Asegúrate de revisar el archivo y actualizar `DATABASE_URL` si quieres conectar una base de datos diferente.

## URLs importantes

- Dashboard local: `http://localhost:8050`
- Documentación OpenAPI: `http://localhost:8000/docs`

## Repositorio GitHub

Este proyecto está publicado en:

https://github.com/CristhianMaylle/parcial.git
