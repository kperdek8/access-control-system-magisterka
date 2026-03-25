# --- KONFIGURACJA (Hardcoded) ---
$VENV_PATH = ".\.venv"

# Definicja par: "wejscie:wyjscie"
$FILES_TO_COMPILE = @(
    "requirements.in:requirements.txt"
    "PDP/requirements.in:PDP/requirements.txt"
    "PEP/requirements.in:PEP/requirements.txt"
    "PIP/requirements.in:PIP/requirements.txt"
)
# -------------------------------

Write-Host "--- Kompilacja requirements.txt ---" -ForegroundColor Cyan

# a) Stworzenie venv, jeżeli nie istnieje
if (-not (Test-Path "$VENV_PATH")) {
    Write-Host "[1] Tworzenie wirtualnego srodowiska..." -ForegroundColor Yellow
    python -m venv $VENV_PATH
}

$PYTHON_EXE = "$VENV_PATH\Scripts\python.exe"
$PIP_COMPILE = "$VENV_PATH\Scripts\pip-compile.exe"

# b) Instalacja pip-tools
if (-not (Test-Path $PIP_COMPILE)) {
    Write-Host "[2] Instalacja pip-tools wewnatrz venv..." -ForegroundColor Yellow
    & $PYTHON_EXE -m pip install --upgrade pip
    & $PYTHON_EXE -m pip install pip-tools
}

Write-Host "[3] Kompilacja plikow..." -ForegroundColor Yellow
foreach ($entry in $FILES_TO_COMPILE) {
    $parts = $entry -split ":"
    $INPUT = $parts[0]
    $OUTPUT = $parts[1]

    if (Test-Path $INPUT) {
        Write-Host "  -> Kompilacja $INPUT do $OUTPUT..."
        & $PYTHON_EXE -m piptools compile --resolver=backtracking --output-file="$OUTPUT" "$INPUT"
    } else {
        Write-Host "  ! POMINIĘTO: Brak pliku $INPUT" -ForegroundColor Red
    }
}

Write-Host "--- Gotowe! ---" -ForegroundColor Green