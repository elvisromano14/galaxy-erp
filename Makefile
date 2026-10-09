.PHONY: help install lint format typecheck test run-api clean init-test test-conn podman-build podman-run podman-stop podman-logs

VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
PIP ?= $(VENV)/bin/pip
RUFF ?= $(VENV)/bin/ruff
MYPY ?= $(VENV)/bin/mypy
PYTEST ?= $(VENV)/bin/pytest
UVICORN ?= $(VENV)/bin/uvicorn

help:
	@echo "Galaxy ERP - Comandos disponibles:"
	@echo "  make install      Instala dependencias en entorno virtual"
	@echo "  make lint         Ejecuta análisis estático con Ruff"
	@echo "  make format       Aplica formateo automático de código con Ruff"
	@echo "  make typecheck    Ejecuta comprobación de tipos con mypy"
	@echo "  make test         Ejecuta suite de pruebas con pytest"
	@echo "  make run-api      Inicia servidor de desarrollo FastAPI en host local"
	@echo "  make init-test    Inicializa y siembra la empresa canario permanente 'test'"
	@echo "  make test-conn    Prueba conexión y operaciones contra el tenant 'test'"
	@echo "  make podman-build Compila imagen OCI de la API con Podman"
	@echo "  make podman-run   Ejecuta contenedor galaxy-api con Podman"
	@echo "  make podman-stop  Detiene y elimina contenedor galaxy-api"
	@echo "  make podman-logs  Muestra logs en tiempo real de galaxy-api"
	@echo "  make clean        Limpia cachés y artefactos temporales"

install:
	@test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e "./api[dev]"

lint:
	$(RUFF) check api

format:
	$(RUFF) format api
	$(RUFF) check --fix api

typecheck:
	PYTHONPATH=api $(MYPY) api/app

test:
	PYTHONPATH=api $(PYTEST) api/tests

run-api:
	PYTHONPATH=api $(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

init-test:
	PYTHONPATH=api $(PYTHON) -m cli.main test init

test-conn:
	PYTHONPATH=api $(PYTHON) scripts/probar_conexion.py

podman-build:
	podman build -t galaxy-api:latest -f api/Containerfile api/

podman-run:
	podman run -d --name galaxy-api --network host --env-file .env galaxy-api:latest

podman-stop:
	podman rm -f galaxy-api

podman-logs:
	podman logs -f galaxy-api

frontend-build:
	podman build -t galaxy-frontend:latest -f mobile/Containerfile mobile/

frontend-run:
	podman run -d --name galaxy-frontend --restart always --network host galaxy-frontend:latest

frontend-stop:
	podman rm -f galaxy-frontend

frontend-logs:
	podman logs -f galaxy-frontend
