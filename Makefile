.PHONY: help install lint format typecheck test run-api clean init-test test-conn

VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
PIP ?= $(VENV)/bin/pip
RUFF ?= $(VENV)/bin/ruff
MYPY ?= $(VENV)/bin/mypy
PYTEST ?= $(VENV)/bin/pytest
UVICORN ?= $(VENV)/bin/uvicorn

help:
	@echo "Galaxy ERP - Comandos disponibles:"
	@echo "  make install     Instala dependencias en entorno virtual"
	@echo "  make lint        Ejecuta análisis estático con Ruff"
	@echo "  make format      Aplica formateo automático de código con Ruff"
	@echo "  make typecheck   Ejecuta comprobación de tipos con mypy"
	@echo "  make test        Ejecuta suite de pruebas con pytest"
	@echo "  make run-api     Inicia servidor de desarrollo FastAPI"
	@echo "  make init-test   Inicializa y siembra la empresa canario permanente 'test'"
	@echo "  make test-conn   Prueba conexión y operaciones contra el tenant 'test'"
	@echo "  make clean       Limpia cachés y artefactos temporales"

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
