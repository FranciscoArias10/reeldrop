#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] No se encontró python3. Instálalo con: sudo apt install python3 python3-venv python3-tk"
    exit 1
fi

# Crear entorno virtual automáticamente en Linux si no existe
if [ ! -d ".venv" ]; then
    echo "Configurando entorno virtual e instalando dependencias por primera vez..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

exec .venv/bin/python app.py "$@"

