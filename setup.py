"""
Script de instalación y arranque del proyecto Olist BI Dashboard.
Ejecutar: python setup.py
"""
import subprocess, sys, os, time

def run(cmd, **kw):
    print(f"  > {cmd}")
    return subprocess.run(cmd, shell=True, **kw)

print("=" * 60)
print("  Olist BI Dashboard — Capítulo 9  ")
print("  Setup & Start                    ")
print("=" * 60)

# 1. Instalar dependencias
print("\n[1/4] Instalando dependencias Python …")
run(f"{sys.executable} -m pip install -r requirements.txt -q")

# 2. Levantar PostgreSQL con Docker
print("\n[2/4] Levantando PostgreSQL con Docker …")
result = run("docker compose up -d postgres", capture_output=True)
if result.returncode != 0:
    print("  ⚠ Docker no disponible o error. Asegúrate de tener Docker Desktop corriendo.")
    print("    Alternativa: instala PostgreSQL manualmente y crea la base 'olist_bi'")
    print("    con usuario 'olist' y contraseña 'olist123'.")
else:
    print("  Esperando que PostgreSQL esté listo …")
    time.sleep(8)

# 3. Sembrar datos
print("\n[3/4] Cargando datos simulados en PostgreSQL …")
env = os.environ.copy()
env["DATABASE_URL"] = "postgresql://olist:olist123@localhost:5432/olist_bi"
r = run(f"{sys.executable} -m backend.seed", env=env, capture_output=False)
if r.returncode != 0:
    print("  ⚠ Error al sembrar datos. Verifica la conexión a PostgreSQL.")

# 4. Instrucciones finales
print("\n[4/4] Para iniciar los servidores, ejecuta en terminales separadas:")
print()
print("  Terminal 1 — Backend API:")
print("    python -m uvicorn backend.main:app --reload --port 8000")
print()
print("  Terminal 2 — Dashboard:")
print("    python dashboard/app.py")
print()
print("  Luego abre: http://localhost:8050")
print("  API docs:   http://localhost:8000/docs")
print()
print("  Conexión DBeaver → PostgreSQL:")
print("    Host: localhost | Puerto: 5432")
print("    Database: olist_bi | User: olist | Password: olist123")
print("=" * 60)
