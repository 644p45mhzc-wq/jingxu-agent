param([switch]$Check)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Test-Python([string]$Executable) {
    if (-not (Test-Path -LiteralPath $Executable)) { return $false }
    try {
        & $Executable -I -c "import sys; assert sys.version_info >= (3,10)" *> $null
        return $LASTEXITCODE -eq 0
    } catch { return $false }
}

# A copied virtual environment may exist but point to another computer.
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Python $taskPython)) {
    Write-Host 'The bundled Python environment is missing or invalid. Using a local environment.'
    $taskPython = Join-Path $PSScriptRoot '.venv-local\Scripts\python.exe'
    if (-not (Test-Python $taskPython)) {
        $taskBase = $null
        $taskLauncher = Get-Command py -ErrorAction SilentlyContinue
        if ($taskLauncher) {
            try {
                $taskCandidate = & $taskLauncher.Source -3.12 -I -c "import sys; print(sys.executable)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $taskCandidate -and (Test-Python ([string]$taskCandidate))) { $taskBase = [string]$taskCandidate }
            } catch {}
        }
        if (-not $taskBase) {
            $taskCommand = Get-Command python -ErrorAction SilentlyContinue
            if ($taskCommand -and (Test-Python $taskCommand.Source)) { $taskBase = $taskCommand.Source }
        }
        if (-not $taskBase) { throw 'Install Python 3.12 and enable Add Python to PATH, then run start.ps1 again.' }
        if ($Check) { Write-Host "Check passed. A fresh environment will be created using: $taskBase"; exit 0 }
        & $taskBase -m venv (Join-Path $PSScriptRoot '.venv-local')
        if ($LASTEXITCODE -ne 0 -or -not (Test-Python $taskPython)) { throw 'Unable to create a local Python environment.' }
    }
}
if ($Check) { Write-Host "Check passed. Working Python environment: $taskPython"; exit 0 }
& $taskPython -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check your internet connection and retry.' }
Write-Host 'Open http://127.0.0.1:8000 in your browser. Keep this terminal open. Press Ctrl+C to stop.'
& $taskPython -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
if ($LASTEXITCODE -ne 0) { throw 'The server stopped with an error. See the message above; port 8000 may already be in use.' }
