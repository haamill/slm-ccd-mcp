param(
    [Parameter(Mandatory=$true)][string]$LocalIp,
    [Parameter(Mandatory=$true)][string]$RemoteAddress,
    [ValidateRange(1,65535)][int]$Port = 8765
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$programPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
New-NetFirewallRule -DisplayName "SLM CCD MCP private LAN $Port" -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -LocalAddress $LocalIp -RemoteAddress $RemoteAddress -Profile Private -Program $programPath
