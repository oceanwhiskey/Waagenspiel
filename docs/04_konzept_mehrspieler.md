# Konzept: Spielername und Spielen gegen andere

Ziel: Man wählt einen Spielernamen und misst sich mit anderen. Es bleibt
schlicht: keine Echtzeit-Technik, keine privaten Daten, keine fremden
Dienste. Alles läuft auf dem vorhandenen Webspace bei Biohost (PHP 7.4, MySQL
über PDO; geprüft am 18.11.2026).

> **Stand November 2026: Spielernamen wurden wieder abgeschafft.** Nach dem
> Ausprobieren (erst mit Übertragungscode, dann mit einem Tag Sperre) war
> beides zu umständlich. Jetzt gilt: Nach jeder vollen Partie auf Zeit kann
> sich jeder mit einem frei gewählten Namen eintragen. Alle Einträge bleiben
> stehen (Tabelle `ws_rekord`: id, kategorie, name, punkte, erreicht). Abschnitt 2 und die Spielernamen-Teile unten beschreiben den
> verworfenen Entwurf; für Duelle und Tagesrätsel müsste man neu überlegen,
> wie Teilnehmer ohne Konto erkannt werden.

## 1. Was es geben soll

| Funktion | Kurz |
|---|---|
| **Spielername** | Ein selbst gewählter Name, an das Gerät gebunden, das ihn zuletzt benutzt hat; nach einem Tag Pause wieder frei. Ohne Namen spielt man weiter wie bisher. |
| **Tagesrätsel** | Jeden Tag dieselben Rätsel für alle, eine Tagesliste. |
| **Duell** | Ich spiele eine Partie, schicke einen Link, der andere spielt *dieselben* Rätsel. Wer mehr Punkte hat, gewinnt. |
| **Bestenliste** | Wie heute, aber Einträge gehören zu Spielernamen statt zu frei getippten Namen. |

Bewusst **nicht**: gleichzeitiges Live-Duell. Dafür bräuchte es eine
dauernde Verbindung (WebSockets), die ein PHP-Webspace nicht gut kann, und es
müssten beide zur selben Zeit online sein. Ein Duell nacheinander mit
denselben Rätseln ist genauso fair und viel einfacher.

## 2. Spielername und Geräteschlüssel

Es gibt kein Passwort und keine E-Mail-Adresse. Das Gerät ist der Ausweis.

1. **Beim ersten Mal** wählt man einen Spielernamen (1–20 Zeichen,
   Buchstaben, Ziffern, Leerzeichen und `. _ - ! ?`, eindeutig ohne Rücksicht
   auf Groß- und Kleinschreibung).
2. **Der Server erzeugt einen Geräteschlüssel**: 32 Zufallsbytes
   (`random_bytes`), als Text etwa 43 Zeichen. Der Browser speichert ihn in
   `localStorage`. Der Server speichert nur `hash('sha256', schlüssel)`.
   Weil der Schlüssel zufällig und lang ist, genügt ein einfacher Hash; ein
   langsames Passwort-Verfahren ist nicht nötig.
3. **Bei jedem Aufruf** schickt der Browser den Schlüssel im Kopf
   `X-Waagenspiel-Schluessel`. (`Authorization` würde Apache bei manchen
   PHP-Einstellungen verschlucken.) Ein Cookie gibt es nicht; damit können
   fremde Seiten auch keine Aufrufe unterschieben.
4. **Ein Name ist einen Tag lang gesperrt.** Er gehört dem Gerät, das ihn
   zuletzt benutzt hat (Name genommen, Partie gestartet oder eingetragen,
   Namensblatt geöffnet). Nach einem Tag ohne Benutzung ist er wieder frei.
   Wer ihn dann eingibt, bekommt ihn samt seinen Ergebnissen; die bisherigen
   Geräte verlieren ihn. So wechselt man das Gerät: einfach am nächsten Tag
   denselben Namen eingeben. Einen Übertragungscode gibt es nicht mehr
   (war zuerst umgesetzt, erschien aber zu umständlich).
5. **Ein anderer Name**: Gibt man auf dem Namensblatt einen anderen Namen
   ein, lässt das Gerät den alten los. Der alte Name bleibt mit seinen
   Ergebnissen stehen und ist nach einem Tag frei.
6. **Auf diesem Gerät abmelden**: Das Gerät vergisst den Namen; der Name
   bleibt mit seinen Ergebnissen bestehen und ist nach einem Tag frei.
7. **Name löschen** geht mit einem Knopf: Name, Geräteschlüssel und alle
   Ergebnisse verschwinden (in fremden Duellen erscheint dann „gelöscht“).

Gespeichert werden damit nur ein ausgedachter Spielername, Hashes der
Geräteschlüssel und Spielergebnisse. Würde die Datenbank gestohlen, ließe sich
mit den Hashes nichts anfangen, und es gibt kein Passwort, das jemand auch
anderswo benutzt.

## 3. Fair spielen: der Server teilt die Rätsel aus

Heute liegt `raetsel.json` vollständig im Browser, und in der kanonischen Form
ist immer `a` die Antwort. Für eine private Partie ist das egal, für Wettkämpfe
nicht. Deshalb gilt in allen Modi mit Spielernamen:

1. Der Server wählt die Rätsel und benennt die Figuren um. Der Browser bekommt
   nur die Waagen, **nicht die Antwort**.
2. Für jede Antwort fragt der Browser den Server: `wahl = 2`. Der Server prüft,
   rechnet die Punkte (Serienfaktor, Abzug nach Bedenkzeit) mit **seiner**
   Uhr und liefert das Ergebnis und das nächste Rätsel.
3. Die Spielzeit misst ebenfalls der Server. Nach Ablauf nimmt er keine
   Antworten mehr an.

Damit sind Punkte nicht mehr fälschbar. Eine Runde kostet einen kurzen
Serveraufruf (etwa 100 ms); das fällt im Spiel nicht auf. Die Bedenkzeit
enthält diese Verzögerung, aber für alle gleich. Ein Restrisiko bleibt: Jemand
könnte ein Programm die Rätsel lösen lassen. Das lässt sich bei einem
Rätselspiel nicht verhindern.

Die Rätsel liegen dafür auf dem Server in einer Tabelle (die 1 600 aus dem
Web-Export, später gern mehr). Tipps gibt es nur beim Üben, nicht im
Wettkampf.

## 4. Spielarten

### 4.1 Tagesrätsel

- Jeden Tag ein fester Satz: 10 Rätsel, aufsteigend von Leicht bis Profi,
  ohne Zeitlimit für den ganzen Satz, aber mit der üblichen Bedenkzeit-Wertung
  pro Rätsel.
- Jeder Spielername kann den Satz **einmal** spielen. Danach sieht man die
  Tagesliste und die Lösungen.
- Auswahl: aus dem Datum abgeleiteter Zufall (`seed = Datum`), damit alle
  dieselben Rätsel bekommen und niemand sie vorher kennt.

### 4.2 Duell

1. A wählt Schwierigkeit und Zeit (wie heute) und tippt auf
   „Herausfordern“. A spielt sofort.
2. Danach gibt es einen **Link** (`imazeki.de/#duell/7KQ2M9`), den A per
   Messenger teilt (auf dem Handy über das Teilen-Menü). Optional kann A auch
   einen Spielernamen eintragen; dann taucht das Duell bei B unter „Offene
   Duelle“ auf.
3. B öffnet den Link, wählt einen Spielernamen (falls noch keiner da ist) und
   spielt **dieselben Rätsel in derselben Reihenfolge**. B sieht As Ergebnis
   erst hinterher.
4. Ergebnisseite für beide: Punkte, Richtig/Falsch, beste Serie, Gewinner.
5. Ein Duell läuft 7 Tage; danach verfällt es. Ein Link kann von mehreren
   angenommen werden („Gruppen-Duell“): dann eine kleine Rangliste.

Damit A nicht vorher üben kann, bekommt jedes Duell einen eigenen Satz
Rätsel (Auswahl mit eigenem Seed). Weil die Zeit begrenzt ist, braucht ein
Duell mehr Rätsel als jemand schafft: Es werden 40 vorbereitet; wer schneller
ist, sieht mehr davon.

### 4.3 Bestenliste

- Wie heute ein Rekord je Schwierigkeit und Zeit, zusätzlich eine
  **Top 10** je Kategorie (sonst ist ein früher Rekord für immer uneinholbar).
- Nur Partien mit Spielernamen zählen; der Name kommt vom Gerät, nicht aus
  einem Eingabefeld. So kann sich niemand als jemand anderes eintragen.
- Ohne Namen spielt man weiter, sieht aber „Wähl einen Spielernamen, damit
  dein Ergebnis zählt“.

## 5. Datenbank

MySQL ist hier sinnvoll: Namen, Geräte, Duelle und Antworten werden
gleichzeitig gelesen und geschrieben und müssen gefiltert werden. Die heutige
JSON-Datei wäre dafür zu einfach. Zugriff nur über PDO mit vorbereiteten
Anweisungen. Die Zugangsdaten stehen in einer Datei außerhalb des
Repositorys und außerhalb des öffentlichen Ordners.

Umgesetzt (Schritt 1, Tabellen mit Präfix `ws_`, legt `inc/gemeinsam.php`
beim ersten Aufruf an):

```text
spieler       id, name, name_klein (eindeutig), erstellt, zuletzt
geraet        id, spieler_id, schluessel_hash (eindeutig), erstellt, zuletzt
ergebnis      spieler_id, kategorie, punkte, erreicht   (bestes je Kategorie)
marke         kennung, benutzt                          (eingelöste Spielmarken)
einstellung   schluessel, wert                          (Geheimnis für Spielmarken)
```

Für Schritt 2 bis 4 kommen dazu:

```text
raetsel       id, stufe, waagen (Text wie "b + c < a")
partie        id, art (frei|tag|duell), code (für Links), stufe, zeit_s,
              seed, erstellt_von, erstellt, ablauf
teilnahme     id, partie_id, spieler_id, begonnen, beendet,
              punkte, richtig, falsch, beste_serie, serie_aktuell
antwort       teilnahme_id, nr, raetsel_id, umbenennung, gezeigt_um,
              wahl, richtig, punkte
```

`antwort.gezeigt_um` ist die Server-Uhrzeit, zu der das Rätsel ausgeliefert
wurde; daraus kommt die Bedenkzeit. Die alte `bestenliste.php` mit ihrer
JSON-Datei kann danach entfallen.

## 6. Schnittstelle (PHP, JSON)

| Aufruf | Zweck |
|---|---|
| `spieler.php` `nehmen` (name) | neuen oder seit einem Tag freien Namen nehmen, liefert Geräteschlüssel; vergeben: 409 mit `frei_ab` |
| `spieler.php` `ich`, `abmelden`, `loeschen` | Name verwalten |
| `partie.php` `start` (art, stufe, zeit, code) | Partie oder Duell beginnen, liefert erstes Rätsel |
| `partie.php` `antwort` (teilnahme, nr, wahl) | prüft, liefert Punkte, Lösung und nächstes Rätsel |
| `partie.php` `ergebnis` (code) | Ergebnisseite eines Duells oder Tagesrätsels |
| `listen.php` `bestenliste`, `tag`, `meine_duelle` | Listen |

Alle Aufrufe außer `nehmen` und den öffentlichen Listen
brauchen den Geräteschlüssel. Höchstens 30 neue Namen pro Stunde und
Server, damit niemand die Datenbank vollschreibt.

## 7. Oberfläche

Startseite (Ergänzungen fett):

```text
  Waagen-Spiel
  [Schwierigkeit]  [Zeit]
  [ Los geht's! ]
  [ Tagesrätsel ]  [ Herausfordern ]
  Bestenliste · Ton: an · **Spielername wählen** (bzw. **Spielername: Ingo**)
```

- **Spielername wählen**: ein Feld, ein Knopf. Mit Namen dazu „Auf diesem
  Gerät abmelden“ und „Name löschen“.
- **Herausfordern**: startet sofort eine Partie mit den gewählten
  Einstellungen; am Ende „Link teilen“.
- **Duell-Link öffnen**: „Ingo fordert dich heraus: Profi, 60 s. Annehmen?“
- **Ergebnis**: zwei Spalten nebeneinander, Gewinner hervorgehoben.

Das Spiel selbst bleibt unverändert. Nur kommen die Rätsel bei Partien mit
Namen vom Server statt aus `raetsel.json`. Üben und freies Spielen ohne Namen
funktionieren weiter offline.

## 8. Datenschutz und Recht

- Gespeichert werden nur: ein selbst gewählter Spielername, Hashes der
  Geräteschlüssel, Spielergebnisse und Zeitpunkte. Kein Passwort, keine
  E-Mail, keine IP-Adressen in der Datenbank.
- Der Geräteschlüssel im Browser ist technisch nötig für die gewählte
  Funktion; ein Einwilligungsbanner braucht es dafür nicht.
- Ein kurzer **Datenschutzhinweis** und ein **Impressum** gehören trotzdem auf
  die Seite (der Webserver protokolliert Zugriffe, und die alte
  `legal notice.html` ist weg). Beides als kurze Seiten, verlinkt unten auf der
  Startseite.
- „Name löschen“ entfernt alle Daten zu diesem Namen.

## 9. Umsetzung in Schritten

1. **Spielername und Bestenliste mit Namen.** Datenbank anlegen,
   `spieler.php`, Namensblatt, Name einen Tag gesperrt, Bestenliste auf
   Spielernamen umstellen, Datenschutzhinweis und Impressum.
2. **Server teilt Rätsel aus.** `raetsel`-Tabelle befüllen, `partie.php`
   für Partien auf Zeit mit Namen; Punkte rechnet der Server.
3. **Tagesrätsel.**
4. **Duelle per Link** und „Meine Duelle“.
5. Später bei Bedarf: Freunde, Statistiken, Live-Duell.

Jeder Schritt ist für sich nutzbar. Schritt 1 und 2 sind der größte Teil;
3 und 4 bauen fast nur noch Listen und Seiten darauf.

## 10. Offene Entscheidungen

| Frage | Vorschlag |
|---|---|
| Tagesrätsel: wie viele, mit Zeitlimit? | 10 Rätsel, ohne Gesamtzeit |
| Duelle nur per Link oder auch gezielt an einen Namen? | beides |
| Bestenliste: nur Rekord oder Top 10? | Top 10 je Kategorie |
| Spiele ohne Namen in der Bestenliste? | nein, nur mit Namen |
| Gelöschte Namen in fremden Duellen? | als „gelöscht“ anzeigen, damit die Gegner ihr Ergebnis behalten |
| Ungenutzte Namen freigeben? | nach einem Jahr ohne Spiel |
