param(
    [string]$ConfigPath = 'config/local.toml',
    [ValidateSet('simulate','hardware')][string]$Mode,
    [string]$TokenFile = 'config/local.token'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not $env:LAB_MCP_TOKEN) {
    $env:LAB_MCP_TOKEN = (Get-Content -LiteralPath $TokenFile -Raw).Trim()
}
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
$serverArgs = @('-m','lab_mcp','serve','--config',$ConfigPath)
if ($Mode) { $serverArgs += @('--mode',$Mode) }
& $pythonPath @serverArgs
exit $LASTEXITCODE
