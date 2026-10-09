$ErrorActionPreference = 'Stop'
$backendRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $backendRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Backend environment is missing. Follow backend/README.md first.'
}
& $pythonPath -m uvicorn app.main:app --app-dir $backendRoot --host 127.0.0.1 --port 8000
exit $LASTEXITCODE
