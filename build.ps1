# Construit dist\AssistantPosture.exe : executable autonome, sans console.
# Prerequis : .\.venv\Scripts\pip install -e ".[dev]" et, une fois, npm --prefix frontend ci (Node 20.19+)
# Pas de $ErrorActionPreference = "Stop" : PowerShell 5.1 traiterait les logs de PyInstaller (stderr) comme une erreur.
# Interface : frontend/ (React + shadcn) compile en un seul fichier, posture\index.html
npm --prefix frontend run build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
.\.venv\Scripts\python -m pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
.\.venv\Scripts\pyinstaller --noconfirm --clean --onefile --windowed --name AssistantPosture `
    --paths . --add-data "posture\index.html;posture" --collect-data mediapipe `
    posture\__main__.py
exit $LASTEXITCODE
