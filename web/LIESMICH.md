# Waagen-Spiel im Browser

Reine statische Seite (HTML, CSS, JavaScript, SVG), ohne Server-Code und ohne
fremde Dienste. Läuft auf dem Handy und am Rechner, lässt sich auf den
Startbildschirm legen und funktioniert danach auch offline.

## Online stellen

1. Den **Inhalt** dieses Ordners `web/` auf den Webspace hochladen, z. B. per
   SFTP nach `imazeki.de/` oder in einen Unterordner wie `imazeki.de/waagen/`.
   Alle Pfade sind relativ, beides funktioniert.
   `LIESMICH.md` und `tests.html` braucht es online nicht.
2. Die Seite muss über **https** erreichbar sein. Nur dann bietet das Handy
   „Zum Startbildschirm hinzufügen“ als App an und speichert sie für offline.
3. `.htaccess` ist für Apache-Webspace gedacht: Sie setzt die richtigen
   Dateitypen, packt die Rätseldatei (1,1 MB → etwa 75 KB) und sperrt die
   Testseite. Bei anderen Servern einfach weglassen.

Auf dem Handy: Seite öffnen, dann im Browser-Menü „Zum Startbildschirm“
(Android: Chrome-Menü ⋮, iPhone: Teilen-Knopf).

## Lokal ausprobieren

```bash
python -m http.server 8000 --directory web
```

Dann <http://localhost:8000> öffnen. Direkt als Datei (`file://`) geht es
nicht, weil die Seite Module und `raetsel.json` nachlädt. Die Tests der
Spiellogik laufen unter <http://localhost:8000/tests.html>.

## Aufbau

| Datei | Inhalt |
|---|---|
| `spiel.js` | Spiellogik ohne Oberfläche: Runden, Partie, Punkte, Stufen, Bestenliste |
| `figuren.js` | SVG-Zeichnungen der Figuren und Waagen |
| `oberflaeche.js` | Bildschirme, Eingaben, Animationen; bekommt die Partie von außen |
| `raetsel.json` | 1 525 Rätsel mit Lösungsschritten, erzeugt mit `python webversion.py` |
| `sw.js`, `manifest.webmanifest`, `icon*` | Installierbar und offline spielbar |

Die Rätsel stammen aus dem exakt geprüften Katalog: Jedes hat genau eine
schwerste Figur, und jede Waage wird gebraucht. Im Browser läuft kein Löser,
deshalb sind die Lösungsschritte vorberechnet. Mehr Rätsel je Stufe:
`python webversion.py --je-stufe 800`.

Bestenliste und Einstellungen liegen nur im Browser des Geräts
(`localStorage`). Es werden keine Daten übertragen.
