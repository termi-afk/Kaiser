# Creates or removes the Kaiser desktop shortcuts. Called by the installer (custom action).
# The desktop can live on another drive (OneDrive), where Windows Installer itself cannot remove
# files without elevation (it backs them up into <drive>:\Config.Msi), so the installer leaves the
# desktop to this script.
param([ValidateSet('create', 'remove')][string]$Action = 'create')
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$desktop = [Environment]::GetFolderPath('Desktop')
$links = @(
  @{ Name = 'Kaiser 1.22a';     Game = 'Kaiser 1.22a'; Icon = 'kaiser122.ico'; Desc = 'Kaiser 1.22a von Stefan Maday' },
  @{ Name = 'Kaiser 1.23 beta'; Game = 'Kaiser 1.23';  Icon = 'kaiser123.ico'; Desc = 'Kaiser 1.23 beta 1 von Stefan Maday' }
)
$shell = New-Object -ComObject WScript.Shell
foreach ($l in $links) {
  $path = Join-Path $desktop "$($l.Name).lnk"
  if ($Action -eq 'remove') {
    if (Test-Path $path) {
      # only remove shortcuts that point into this installation
      $target = $shell.CreateShortcut($path).Arguments
      if ($target -like "*$root*") { Remove-Item $path -Force }
    }
    continue
  }
  $s = $shell.CreateShortcut($path)
  $s.TargetPath = Join-Path $root 'otvdm\otvdmw.exe'
  $s.Arguments = '"' + (Join-Path $root "$($l.Game)\KAISER.EXE") + '"'
  $s.WorkingDirectory = Join-Path $root $l.Game
  $s.IconLocation = (Join-Path $root "icons\$($l.Icon)") + ',0'
  $s.Description = $l.Desc
  $s.Save()
}
