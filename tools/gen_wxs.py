r"""Generate the WiX v5 source for the Kaiser installer from a staged payload tree.

Usage: gen_wxs.py <payload_dir> <icons_dir> <data_dir> <out.wxs> <version>

payload_dir layout (made by build.ps1):
    Kaiser 1.22a\   KAISER.EXE, KAISER.HLP, kaiser.mid, versions.txt
    Kaiser 1.23\    KAISER.EXE, KAISER.HLP (1.22a help for the "?" buttons), kaiser.mid,
                    Kaiser 1.23 Hilfe.html, Hilfe\bm*.png
    otvdm\          otvdm 0.9.0 (WINDOWS\kaiser.ini preset: 800x600)

Per-user install into %LOCALAPPDATA%\Programs\Kaiser (writable: Kaiser saves its games next to
KAISER.EXE, otvdm writes kaiser.ini into its WINDOWS folder). One component per directory with an
HKCU KeyPath and a RemoveFolder (removes only empty folders, so savegames survive an uninstall).
"""
import hashlib
import os
import sys
import uuid
from xml.sax.saxutils import quoteattr as q

PAYLOAD, ICONS, DATA, OUT, VERSION = sys.argv[1:6]
UPGRADE_CODE = "6B1C3E52-7A0D-4E8B-9C51-2F4A8D0B1E22"  # never change: enables upgrades
NS = uuid.UUID(UPGRADE_CODE)
REG = r"Software\Kaiser"
G122, G123, OTVDM = "Kaiser 1.22a", "Kaiser 1.23", "otvdm"


def ident(prefix, rel):
    return prefix + hashlib.sha1(rel.lower().encode()).hexdigest()[:20]


def did(rel):
    return "INSTALLFOLDER" if rel == "" else ident("d", rel)


def dir_xml(rel, indent):
    out = []
    for name in sorted(os.listdir(os.path.join(PAYLOAD, rel)), key=str.lower):
        sub = os.path.join(rel, name)
        if os.path.isdir(os.path.join(PAYLOAD, sub)):
            out.append("  " * indent + f'<Directory Id="{did(sub)}" Name={q(name)}>')
            out += dir_xml(sub, indent + 1)
            out.append("  " * indent + "</Directory>")
    return out


def components():
    out = []
    for cur, dirs, files in os.walk(PAYLOAD):
        dirs.sort(key=str.lower)
        rel = os.path.relpath(cur, PAYLOAD)
        rel = "" if rel == "." else rel
        cid = ident("c", rel or "<root>")
        guid = str(uuid.uuid5(NS, "dir:" + rel.lower())).upper()
        out.append(f'      <Component Id="{cid}" Directory="{did(rel)}" Guid="{guid}">')
        out.append(f'        <RegistryValue Root="HKCU" Key="{REG}\\Components" Name="{cid}" Type="integer" Value="1" KeyPath="yes" />')
        out.append(f'        <RemoveFolder Id="rm{cid}" On="uninstall" />')
        settings = []
        for f in sorted(files, key=str.lower):
            src = os.path.join(PAYLOAD, rel, f)
            if f.lower() == "kaiser.ini":
                settings.append((f, src))
                continue
            out.append(f'        <File Id="{ident("f", os.path.join(rel, f))}" Source={q(src)} />')
        out.append("      </Component>")
        # Settings presets: installed once, never overwritten (repair/upgrade) and left in place
        # on uninstall, so whatever the player changed in the game survives.
        for f, src in settings:
            sid = ident("s", os.path.join(rel, f))
            sguid = str(uuid.uuid5(NS, "settings:" + os.path.join(rel, f).lower())).upper()
            out.append(f'      <Component Id="{sid}" Directory="{did(rel)}" Guid="{sguid}" NeverOverwrite="yes" Permanent="yes">')
            out.append(f'        <File Id="{ident("f", os.path.join(rel, f))}" Source={q(src)} KeyPath="yes" />')
            out.append("      </Component>")
    return out


def shortcut(sid, name, desc, target, args, wd, icon, directory=None):
    d = f' Directory="{directory}"' if directory else ""
    a = f' Arguments="&quot;{args}&quot;"' if args else ""
    return (f'        <Shortcut Id="{sid}"{d} Name={q(name)} Description={q(desc)}\n'
            f'                  Target="{target}"{a} WorkingDirectory="{wd}" Icon="{icon}" />')


g122, g123, ot = did(G122), did(G123), did(OTVDM)
run = f"[{ot}]otvdmw.exe"
shortcuts = "\n".join([
    shortcut("S122", "Kaiser 1.22a", "Kaiser 1.22a von Stefan Maday", run, f"[{g122}]KAISER.EXE", g122, "Icon122"),
    shortcut("S122H", "Kaiser 1.22a Hilfe", "Hilfe zu Kaiser 1.22a", f"[{ot}]winhlp32.exe", f"[{g122}]KAISER.HLP", g122, "IconHelp"),
    shortcut("S123", "Kaiser 1.23 beta", "Kaiser 1.23 beta 1 von Stefan Maday", run, f"[{g123}]KAISER.EXE", g123, "Icon123"),
    shortcut("S123H", "Kaiser 1.23 Hilfe", "Handbuch zu Kaiser 1.23 (HTML)", f"[{g123}]Kaiser 1.23 Hilfe.html", None, g123, "IconHelp"),
    '        <Shortcut Id="SUninst" Name="Kaiser deinstallieren"'
    ' Description="Kaiser entfernen (wahlweise mit Spielständen und Einstellungen)"\n'
    '                  Target="[System64Folder]msiexec.exe" Arguments="/i [ProductCode]" Icon="IconUninst" />',
])

# Uninstall option: a page after "Entfernen" in the maintenance UI with a checkbox. When ticked,
# util:RemoveFolderEx deletes the whole install folder (savegames, KAISER.INI, otvdm\C).
# Without UI (Settings > Apps > Deinstallieren) the data is kept; msiexec /x ... REMOVEDATA=1 purges.
REMOVE_UI = r"""
    <!-- Desktop shortcuts are made by desktop-links.ps1, not by the Shortcut table: removing a file
         on another drive (desktop in OneDrive on D:) makes Windows Installer back it up into
         D:\Config.Msi, which a non-elevated per-user install may not secure (warning, error 5). -->
    <SetProperty Id="DesktopLinksCreate" Sequence="execute" Before="DesktopLinksCreate"
                 Value="&quot;[System64Folder]WindowsPowerShell\v1.0\powershell.exe&quot; -NoProfile -NonInteractive -ExecutionPolicy Bypass -File &quot;[INSTALLFOLDER]desktop-links.ps1&quot; create" />
    <SetProperty Id="DesktopLinksRemove" Sequence="execute" Before="DesktopLinksRemove"
                 Value="&quot;[System64Folder]WindowsPowerShell\v1.0\powershell.exe&quot; -NoProfile -NonInteractive -ExecutionPolicy Bypass -File &quot;[INSTALLFOLDER]desktop-links.ps1&quot; remove" />
    <CustomAction Id="DesktopLinksCreate" BinaryRef="Wix4UtilCA_X64" DllEntry="WixQuietExec"
                  Execute="deferred" Impersonate="yes" Return="ignore" />
    <CustomAction Id="DesktopLinksRemove" BinaryRef="Wix4UtilCA_X64" DllEntry="WixQuietExec"
                  Execute="deferred" Impersonate="yes" Return="ignore" />
    <InstallExecuteSequence>
      <Custom Action="DesktopLinksRemove" Before="RemoveFiles" Condition="REMOVE" />
      <Custom Action="DesktopLinksCreate" After="InstallFiles" Condition="NOT REMOVE" />
    </InstallExecuteSequence>
    <Property Id="DISABLEROLLBACK" Value="1" />
    <Property Id="REMOVEDATA" Secure="yes" />
    <Property Id="KAISERDIR">
      <RegistrySearch Id="FindKaiserDir" Root="HKCU" Key="@REG@" Name="InstallDir" Type="raw" />
    </Property>
    <SetProperty Id="PURGEDIR" Value="[KAISERDIR]" Before="Wix4RemoveFoldersEx_X64" Sequence="execute"
                 Condition="REMOVEDATA = 1 AND REMOVE AND KAISERDIR AND NOT UPGRADINGPRODUCTCODE" />

    <UI>
      <Dialog Id="RemoveDataDlg" Width="370" Height="270" Title="!(loc.MaintenanceTypeDlg_Title)">
        <Control Id="BannerBitmap" Type="Bitmap" X="0" Y="0" Width="370" Height="44" TabSkip="no" Text="!(loc.MaintenanceTypeDlgBannerBitmap)" />
        <Control Id="BannerLine" Type="Line" X="0" Y="44" Width="370" Height="0" />
        <Control Id="Title" Type="Text" X="15" Y="6" Width="340" Height="15" Transparent="yes" NoPrefix="yes" Text="{\WixUI_Font_Title}Kaiser entfernen" />
        <Control Id="Description" Type="Text" X="25" Y="23" Width="340" Height="15" Transparent="yes" NoPrefix="yes" Text="Was soll mit Euren Spielständen und Einstellungen geschehen?" />
        <Control Id="Info" Type="Text" X="25" Y="60" Width="320" Height="60" NoPrefix="yes"
                 Text="Spielstände (*.KSR) und Einstellungen (KAISER.INI, z. B. Auflösung und Musik) liegen im Installationsordner. Normalerweise bleiben sie erhalten und werden bei einer späteren Neuinstallation wieder verwendet." />
        <Control Id="PurgeCheck" Type="CheckBox" X="25" Y="130" Width="320" Height="18" Property="REMOVEDATA" CheckBoxValue="1"
                 Text="Auch alle Spielstände und Einstellungen löschen" />
        <Control Id="Folder" Type="Text" X="40" Y="152" Width="305" Height="30" NoPrefix="yes" Text="Ordner: [KAISERDIR]" />
        <Control Id="BottomLine" Type="Line" X="0" Y="234" Width="370" Height="0" />
        <Control Id="Back" Type="PushButton" X="180" Y="243" Width="56" Height="17" Text="!(loc.WixUIBack)">
          <Publish Event="NewDialog" Value="MaintenanceTypeDlg" />
        </Control>
        <Control Id="Next" Type="PushButton" X="236" Y="243" Width="56" Height="17" Default="yes" Text="!(loc.WixUINext)">
          <Publish Event="NewDialog" Value="VerifyReadyDlg" />
        </Control>
        <Control Id="Cancel" Type="PushButton" X="304" Y="243" Width="56" Height="17" Cancel="yes" Text="!(loc.WixUICancel)">
          <Publish Event="SpawnDialog" Value="CancelDlg" />
        </Control>
      </Dialog>
      <Publish Dialog="MaintenanceTypeDlg" Control="RemoveButton" Event="NewDialog" Value="RemoveDataDlg" Order="10" />
      <Publish Dialog="VerifyReadyDlg" Control="Back" Event="NewDialog" Value="RemoveDataDlg" Order="10"
               Condition="WixUI_InstallMode = &quot;Remove&quot;" />
    </UI>
""".replace("@REG@", REG)

wxs = f"""<?xml version="1.0" encoding="utf-8"?>
<!-- generated by tools/gen_wxs.py -->
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs"
     xmlns:ui="http://wixtoolset.org/schemas/v4/wxs/ui"
     xmlns:util="http://wixtoolset.org/schemas/v4/wxs/util">
  <Package Name="Kaiser 1.22a und 1.23" Manufacturer="Stefan Maday" Version="{VERSION}"
           UpgradeCode="{UPGRADE_CODE}" Scope="perUser" Language="1031" Codepage="1252">
    <SummaryInformation Description="Kaiser 1.22a und 1.23 beta (Windows 3.1) mit otvdm für Windows 10/11" />
    <MajorUpgrade DowngradeErrorMessage="Eine neuere Version des Kaiser-Pakets ist bereits installiert." />
    <MediaTemplate EmbedCab="yes" CompressionLevel="high" />

    <Icon Id="Icon122" SourceFile={q(os.path.join(ICONS, "kaiser122.ico"))} />
    <Icon Id="Icon123" SourceFile={q(os.path.join(ICONS, "kaiser123.ico"))} />
    <Icon Id="IconHelp" SourceFile={q(os.path.join(ICONS, "help.ico"))} />
    <Icon Id="IconUninst" SourceFile={q(os.path.join(ICONS, "uninstall.ico"))} />
    <Property Id="ARPPRODUCTICON" Value="Icon122" />
    <Property Id="ARPURLINFOABOUT" Value="https://github.com/termi-afk/Kaiser" />

    <ui:WixUI Id="WixUI_Minimal" />
    <WixVariable Id="WixUILicenseRtf" Value={q(os.path.join(DATA, "license.rtf"))} />
{REMOVE_UI}

    <StandardDirectory Id="LocalAppDataFolder">
      <Directory Id="LocalPrograms" Name="Programs">
        <Directory Id="INSTALLFOLDER" Name="Kaiser">
{chr(10).join(dir_xml("", 5))}
        </Directory>
      </Directory>
    </StandardDirectory>
    <StandardDirectory Id="ProgramMenuFolder">
      <Directory Id="MenuDir" Name="Kaiser" />
    </StandardDirectory>
    <StandardDirectory Id="DesktopFolder" />

    <Feature Id="Main" Title="Kaiser" Level="1">
      <ComponentGroupRef Id="Payload" />
      <ComponentRef Id="Shortcuts" />
      <ComponentRef Id="LocalProgramsDir" />
    </Feature>
  </Package>

  <Fragment>
    <Component Id="LocalProgramsDir" Directory="LocalPrograms" Guid="{str(uuid.uuid5(NS, 'localprograms')).upper()}">
      <RegistryValue Root="HKCU" Key="{REG}" Name="InstallDir" Type="string" Value="[INSTALLFOLDER]" KeyPath="yes" />
      <RemoveFolder Id="rmLocalPrograms" On="uninstall" />
      <util:RemoveFolderEx Id="PurgeKaiser" On="uninstall" Property="PURGEDIR" />
    </Component>

    <Component Id="Shortcuts" Directory="MenuDir" Guid="{str(uuid.uuid5(NS, 'shortcuts-v2')).upper()}">
{shortcuts}
      <RemoveFolder Id="rmMenuDir" On="uninstall" />
      <RegistryValue Root="HKCU" Key="{REG}" Name="Shortcuts" Type="integer" Value="1" KeyPath="yes" />
    </Component>

    <ComponentGroup Id="Payload">
{chr(10).join(components())}
    </ComponentGroup>
  </Fragment>
</Wix>
"""
open(OUT, "w", encoding="utf-8").write(wxs)
print("wrote", OUT)
