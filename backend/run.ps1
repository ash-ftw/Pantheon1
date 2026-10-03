param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoReload
)

$reloadArg = if ($NoReload) { "" } else { "--reload" }

if (Test-Path ".\.venv\Scripts\python.exe") {
    & .\.venv\Scripts\python.exe -m uvicorn app.main:app --host $Host --port $Port $reloadArg
} else {
    python -m uvicorn app.main:app --host $Host --port $Port $reloadArg
}
