#!/bin/bash

echo "--- Kompilacja requirements.txt ---"

VENV_PATH="./.venv"
FILES_TO_COMPILE=(
    "requirements.in:requirements.txt"
    "PDP/requirements.in:PDP/requirements.txt"
    "PEP/requirements.in:PEP/requirements.txt"
    "PIP/requirements.in:PIP/requirements.txt"
)

# a) Stworzenie venv, jeżeli nie istnieje
if [ ! -d "$VENV_PATH" ]; then
    echo "[1/3] Tworzenie wirtualnego środowiska w: $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
else
    echo "[1/3] Venv już istnieje. Pomijam tworzenie."
fi

source "$VENV_PATH/bin/activate"

# b) Instalacja pip-tools
if [ ! -f "$VENV_PATH/bin/pip-compile" ]; then
    echo "[2] Instalcja pip-tools wewnątrz venv..."
    "$VENV_PATH/bin/python" -m pip install --upgrade pip
    "$VENV_PATH/bin/python" -m pip install pip-tools --force-reinstall
else
    echo "[2] pip-compile znaleziony w $VENV_PATH/bin/."
fi

# c) Kompilacja requirements.txt
echo "[3] Kompilacja plików..."

for entry in "${FILES_TO_COMPILE[@]}"; do
    # Rozdzielenie wejścia od wyjścia za pomocą dwukropka
    INPUT="${entry%%:*}"
    OUTPUT="${entry#*:}"

    if [ -f "$INPUT" ]; then
        echo "  -> Kompilacja $INPUT do $OUTPUT..."
        pip-compile --resolver=backtracking --output-file="$OUTPUT" "$INPUT"
    else
        echo "  ! POMINIĘTO: Brak pliku $INPUT"
    fi
done