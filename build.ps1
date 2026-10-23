# Construit dist\AssistantPosture.exe : executable autonome, sans console.
# Prerequis : .\.venv\Scripts\pip install -e ".[dev]"
# Pas de $ErrorActionPreference = "Stop" : PowerShell 5.1 traiterait les logs de PyInstaller (stderr) comme une erreur.
.\.venv\Scripts\python -m pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
.\.venv\Scripts\pyinstaller --noconfirm --clean --onefile --windowed --name AssistantPosture `
    --paths . --add-data "posture\index.html;posture" --collect-data mediapipe `
    posture\__main__.py
exit $LASTEXITCODE
