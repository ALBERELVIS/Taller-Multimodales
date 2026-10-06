# Descarga el Python 3.12 oficial (binarios firmados por la Python Software Foundation)
# desde NuGet y lo descomprime en .tools\python312. Usamos esta via en lugar del Python
# que gestiona uv porque Smart App Control de Windows 11 bloquea DLL sin firmar.
param([Parameter(Mandatory = $true)][string]$Target)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$versions = (Invoke-RestMethod "https://api.nuget.org/v3-flatcontainer/python/index.json").versions
$v = $versions | Where-Object { $_ -match '^3\.12\.\d+$' } | Select-Object -Last 1
Write-Host "    Python $v"
$zip = Join-Path $Target "python.zip"
$tmp = Join-Path $Target "pynuget"
New-Item -ItemType Directory -Force -Path $Target | Out-Null
Invoke-WebRequest "https://api.nuget.org/v3-flatcontainer/python/$v/python.$v.nupkg" -OutFile $zip
Expand-Archive $zip -DestinationPath $tmp -Force
Move-Item (Join-Path $tmp "tools") (Join-Path $Target "python312")
Remove-Item -Recurse -Force $tmp, $zip
