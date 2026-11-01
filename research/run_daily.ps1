$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$taskPython = Join-Path $projectRoot '.venv-local/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run start.ps1 once to create .venv-local, or run python -m research.daily in your project environment.' }
& $taskPython -m research.daily
exit $LASTEXITCODE
