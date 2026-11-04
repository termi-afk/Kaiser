# Kaiser – Installer für Windows 10/11

Ein Windows-Installer (MSI) für das Strategiespiel **Kaiser** von Stefan Maday, eine Hommage an den
C64-Klassiker. Er installiert beide Versionen nebeneinander:

| | Version | Hilfe |
|---|---|---|
| **Kaiser 1.22a** | letzte offizielle Version (2004), aus dem Originalarchiv `Kai122a.zip` | originale `KAISER.HLP` |
| **Kaiser 1.23 beta 1** | neuere Version mit Wirtshaus u. a. | Handbuch der 1.23 als HTML mit Bildern |

Kaiser ist ein 16-Bit-Programm für Windows 3.1, das ein 64-Bit-Windows nicht mehr starten kann.
Der Installer bringt deshalb [otvdm/winevdm](https://github.com/otya128/winevdm) mit: Die Spiele laufen
damit direkt unter Windows 11, in voller Farbtiefe und mit Musik und Soundeffekten, ganz ohne Emulator.

## Installieren

1. Die neueste `Kaiser-*-Setup.msi` unter [Releases](../../releases) herunterladen.
2. Doppelklicken. Installiert wird nur für den aktuellen Benutzer nach `%LOCALAPPDATA%\Programs\Kaiser`,
   Administratorrechte sind nicht nötig, und systemweit wird nichts geändert.
3. Starten über das Startmenü (Ordner **Kaiser**) oder die Desktop-Verknüpfungen.

800×600, Musik und Soundeffekte sind voreingestellt (im Spiel: *Einstellungen*). Was Ihr im Spiel
umstellt, speichert Kaiser in seiner `KAISER.INI` im Installationsordner. Ein Update oder eine Reparatur
überschreibt diese Datei nie.

## Deinstallieren

- **Startmenü → Kaiser → Kaiser deinstallieren** (oder *Einstellungen → Apps → Kaiser → Ändern*):
  *Entfernen* wählen. Auf der nächsten Seite legt Ihr fest, ob **Spielstände und Einstellungen** erhalten
  bleiben (Standard) oder **mit gelöscht** werden.
- *Einstellungen → Apps → Deinstallieren* entfernt das Programm und behält Spielstände und Einstellungen.
- Per Befehl alles löschen: `msiexec /x Kaiser-…-Setup.msi REMOVEDATA=1`

## Selbst bauen

Das Repository enthält **keine Spieldateien**. `build.ps1` lädt alles bei jedem Build herunter und prüft
die SHA-256-Prüfsummen:

| Quelle | Inhalt |
|---|---|
| [Internet Archive](https://web.archive.org/web/20050119184711/http://yadam.de:80/KAISER/Kai122a.zip): `Kai122a.zip` von yadam.de (Website des Autors) | Kaiser 1.22a |
| [LarsGehrmann/Kaiser-decompile](https://github.com/LarsGehrmann/Kaiser-decompile) Release v1.0.2 | `kaiser.exe` und `kaiser.mid` 1.23, `docs/manual.md` |
| [otya128/winevdm](https://github.com/otya128/winevdm) Release v0.9.0 | otvdm |

Voraussetzungen: Windows, Python 3 mit Pillow und das .NET SDK 8 oder neuer (für das WiX-5-Tool, das das
Skript bei Bedarf selbst installiert).

```powershell
./build.ps1            # -> out\Kaiser-1.23.1-Setup.msi
```

GitHub Actions baut bei jedem Push. Ein Tag `v*` erstellt ein Release mit dem MSI.

### Wie die 1.23-Hilfe entsteht

Die `KAISER.HLP` der 1.23 ist nicht öffentlich verfügbar. Kaiser-decompile enthält aber ihren vollständigen
Text als `docs/manual.md`. Die Bilder dazu kommen aus zwei Quellen:

- `tools/hlp_bitmaps.py` liest die eingebetteten Bitmaps der 1.22a-Hilfe (WinHelp-3.1-Format).
- `tools/ne_bitmaps.py` liest die Symbole der Buttonleiste aus der 1.23-EXE.

Welches Bild zu welcher Nummer der 1.23 gehört, steht in `data/pictures.json`. Ermittelt wurde das mit
`tools/dev/` (Text der 1.22a-Hilfe ausgelesen und gegen das 1.23-Handbuch abgeglichen) und dann von Hand
geprüft. `tools/md_to_html.py` erzeugt daraus die HTML-Seite.

| Werkzeug | Zweck |
|---|---|
| `tools/ne_icon.py` | Icon einer 16-Bit-EXE (NE) oder 32-/64-Bit-EXE (PE) als `.ico` (Verknüpfungen) |
| `tools/gen_wxs.py` | WiX-Quelle aus dem Payload-Ordner |

## Rechtliches

*Kaiser* mit Grafiken, Texten, Musik und Handbuch ist © Stefan Maday. Das Spiel wurde auf der Website des
Autors als Freeware angeboten. Dieses Repository enthält nur die Build-Skripte (MIT-Lizenz, siehe `LICENSE`).
otvdm steht unter der GPL v2. Wer Rechte an den Inhalten hat und widerspricht, öffnet bitte ein Issue.
