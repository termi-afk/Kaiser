<#
.SYNOPSIS
  Builds Kaiser-<version>-Setup.msi (Kaiser 1.22a + 1.23 beta + otvdm) from public downloads.

.DESCRIPTION
  Nothing of the game is stored in this repository. The script downloads (pinned by SHA-256):
    * Kaiser 1.22a     Kai122a.zip, the author's original archive, from the Internet Archive
    * Kaiser 1.23 beta kaiser.exe, kaiser.mid and docs/manual.md from the release zip of
                       github.com/LarsGehrmann/Kaiser-decompile
    * otvdm 0.9.0      github.com/otya128/winevdm
  and builds the MSI with WiX 5 into .\out.

  Requirements: Windows, Python 3 with Pillow, .NET SDK 8+ (for the WiX dotnet tool).
#>
param(
  [string]$Version = '1.23.1',
  [string]$Out = "$PSScriptRoot\out",
  [string]$Cache = "$PSScriptRoot\.cache"
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$py = if (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { 'py' }

$sources = @{
  k122  = @{ Url = 'https://web.archive.org/web/20050119184711id_/http://yadam.de:80/KAISER/Kai122a.zip'
             File = 'Kai122a.zip'; Sha256 = 'b57fd65bf067f3a79542e18b8e4e857db09217adcffe75ebfc48fea88e15ff4c' }
  k123  = @{ Url = 'https://github.com/LarsGehrmann/Kaiser-decompile/releases/download/v1.0.2/Kaiser-Classic-1.0.2-Windows-x64.zip'
             File = 'Kaiser-Classic-1.0.2-Windows-x64.zip'; Sha256 = 'baaf6f214a2477686b6b7c13be3fb42708b54ba1a6b0502b764fe8063c812e9f' }
  otvdm = @{ Url = 'https://github.com/otya128/winevdm/releases/download/v0.9.0/otvdm-v0.9.0.zip'
             File = 'otvdm-v0.9.0.zip'; Sha256 = '842b11aed5fa81f3e1d4272e0ee7d37f1a5a8f936de825309dda672835e16fd4' }
}

function Get-Source($s) {
  New-Item -ItemType Directory -Force $Cache | Out-Null
  $path = Join-Path $Cache $s.File
  if (-not (Test-Path $path) -or (Get-FileHash $path -Algorithm SHA256).Hash -ne $s.Sha256.ToUpper()) {
    Write-Host "download $($s.Url)"
    for ($try = 1; ; $try++) {
      try { Invoke-WebRequest $s.Url -OutFile $path -UseBasicParsing; break }
      catch { if ($try -ge 4) { throw }; Start-Sleep -Seconds (5 * $try) }
    }
  }
  $hash = (Get-FileHash $path -Algorithm SHA256).Hash
  if ($hash -ne $s.Sha256.ToUpper()) { throw "SHA-256 mismatch for $($s.File): $hash" }
  return $path
}

function Expand-To($zip, $dest) {
  Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue
  Expand-Archive $zip -DestinationPath $dest -Force
}

# --- tools ------------------------------------------------------------------------------------
$wix = Join-Path $env:USERPROFILE '.dotnet\tools\wix.exe'
if (-not (Test-Path $wix)) { dotnet tool install --global wix --version 5.0.2 | Out-Host }
foreach ($ext in 'WixToolset.UI.wixext', 'WixToolset.Util.wixext') {
  if (-not ((& $wix extension list -g) -match "$ext 5.0.2")) { & $wix extension add -g "$ext/5.0.2" | Out-Host }
}
& $py -c "import PIL" 2>$null; if ($LASTEXITCODE) { & $py -m pip install --quiet pillow }

# --- download + unpack ------------------------------------------------------------------------
$b = Join-Path $PSScriptRoot 'build'
Remove-Item $b -Recurse -Force -ErrorAction SilentlyContinue
$raw = "$b\raw"; $payload = "$b\payload"; $icons = "$b\icons"
Expand-To (Get-Source $sources.k122) "$raw\k122"
Expand-To (Get-Source $sources.k123) "$raw\k123"
Expand-To (Get-Source $sources.otvdm) "$raw\otvdm"

$p122 = "$payload\Kaiser 1.22a"; $p123 = "$payload\Kaiser 1.23"; $pot = "$payload\otvdm"
New-Item -ItemType Directory -Force $p122, $p123, "$p123\Hilfe", $pot, $icons | Out-Null
foreach ($f in 'KAISER.EXE', 'KAISER.HLP', 'kaiser.mid', 'versions.txt') { Copy-Item "$raw\k122\$f" $p122 }
$c = "$raw\k123\Kaiser Classic"
Copy-Item "$c\Kaiser\kaiser.exe" "$p123\KAISER.EXE"
Copy-Item "$c\Kaiser\kaiser.mid" "$p123\kaiser.mid"
Copy-Item "$raw\k122\KAISER.HLP" "$p123\KAISER.HLP"   # 1.23's own .HLP is not public; keeps the "?" buttons working
$ot = Get-ChildItem "$raw\otvdm" -Directory | Select-Object -First 1
Copy-Item "$($ot.FullName)\*" $pot -Recurse
Remove-Item "$pot\*.lnk" -ErrorAction SilentlyContinue
Copy-Item data\kaiser.ini "$pot\WINDOWS\kaiser.ini"   # 1.22a reads WINDOWS\kaiser.ini: 800x600, sound + music on
Copy-Item data\kaiser123.ini "$p123\KAISER.INI"      # 1.23 keeps its KAISER.INI next to the EXE: same preset
Get-ChildItem $payload -Recurse -File | ForEach-Object { $_.IsReadOnly = $false }

# --- icons ------------------------------------------------------------------------------------
& $py -I tools\ne_icon.py "$p122\KAISER.EXE" "$icons\kaiser122.ico"
& $py -I tools\ne_icon.py "$p123\KAISER.EXE" "$icons\kaiser123.ico"
& $py -I tools\ne_icon.py "$pot\winhlp32.exe" "$icons\help.ico"
& $py -I tools\ne_icon.py "$env:SystemRoot\System32\msiexec.exe" "$icons\uninstall.ico"
New-Item -ItemType Directory -Force "$payload\icons" | Out-Null                 # for desktop-links.ps1
Copy-Item "$icons\kaiser122.ico", "$icons\kaiser123.ico" "$payload\icons\"
Copy-Item data\desktop-links.ps1 $payload

# --- 1.23 help as HTML with its pictures ------------------------------------------------------
& $py -I tools\hlp_bitmaps.py "$p122\KAISER.HLP" "$b\pics122" | Out-Null
& $py -I tools\ne_bitmaps.py "$p123\KAISER.EXE" "$b\bmp123" | Out-Null
$map = (Get-Content data\pictures.json -Raw | ConvertFrom-Json).map
foreach ($prop in $map.PSObject.Properties) {
  $kind, $id = $prop.Value -split ':', 2
  $src = if ($kind -eq 'hlp122') { "$b\pics122\$id.png" } else { "$b\bmp123\$id.png" }
  Copy-Item $src "$p123\Hilfe\$($prop.Name).png"
}
& $py -I tools\md_to_html.py "$c\docs\manual.md" "$p123\Kaiser 1.23 Hilfe.html" Hilfe
if ($LASTEXITCODE) { throw 'md_to_html failed' }

# --- MSI --------------------------------------------------------------------------------------
& $py -I tools\gen_wxs.py $payload $icons (Resolve-Path data) "$b\Kaiser.wxs" $Version
New-Item -ItemType Directory -Force $Out | Out-Null
$msi = Join-Path $Out "Kaiser-$Version-Setup.msi"
& $wix build "$b\Kaiser.wxs" -ext WixToolset.UI.wixext -ext WixToolset.Util.wixext -culture de-DE -arch x64 -o $msi
if ($LASTEXITCODE) { throw "wix build failed ($LASTEXITCODE)" }
Remove-Item ([IO.Path]::ChangeExtension($msi, '.wixpdb')) -ErrorAction SilentlyContinue
$h = (Get-FileHash $msi -Algorithm SHA256).Hash.ToLower()
"$h  $(Split-Path $msi -Leaf)" | Set-Content "$msi.sha256"
Write-Host "built $msi ($([math]::Round((Get-Item $msi).Length / 1MB, 2)) MB) sha256 $h"
