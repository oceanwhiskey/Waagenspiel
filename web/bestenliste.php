<?php
// Globale Bestenliste des Waagen-Spiels.
//
// Je Kategorie (Schwierigkeit/Zeit, z. B. "Mittel/60s") gibt es einen Rekord.
// Eintragen darf sich nur, wer ihn bricht. Die Daten liegen als JSON in einem
// gesperrten Unterordner; der geheime Schluessel fuer die Spielmarken entsteht
// beim ersten Aufruf auf dem Server und steht deshalb in keinem Repository.
//
//   GET  bestenliste.php                       -> {"rekorde": {kategorie: {...}}}
//   POST bestenliste.php  aktion=start         -> {"marke": "..."}   (beim Spielstart)
//   POST bestenliste.php  aktion=eintragen     -> {"ok": true, "rekorde": {...}}
//        Felder: marke, kategorie, punkte, name
//
// Schutz gegen einfaches Schummeln: Die Marke ist signiert, nur einmal gueltig
// und erst nach Ablauf der Spielzeit einloesbar; die Punkte muessen zur
// Spielzeit passen. Wer es darauf anlegt, kann im Browser trotzdem schummeln.

declare(strict_types=1);

const DATEN_ORDNER = __DIR__ . '/bestenliste-daten';
const STUFEN = ['Steigend', 'Leicht', 'Mittel', 'Schwer', 'Profi'];
const ZEITEN = [30, 60, 90, 120];
const PUNKTE_JE_SEKUNDE = 60;   // hoechstens 60 Punkte je Runde, mindestens 1 s je Runde
const VERLAUF = 5;              // so viele fruehere Rekorde je Kategorie bleiben stehen

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function antwort(array $daten, int $status = 200): void {
    http_response_code($status);
    echo json_encode($daten, JSON_UNESCAPED_UNICODE);
    exit;
}

function fehler(string $text, int $status = 400): void {
    antwort(['ok' => false, 'fehler' => $text], $status);
}

function ordner(): void {
    if (!is_dir(DATEN_ORDNER) && !@mkdir(DATEN_ORDNER, 0700)) {
        fehler('Speicher nicht verfuegbar', 500);
    }
    $sperre = DATEN_ORDNER . '/.htaccess';
    if (!is_file($sperre)) {
        file_put_contents($sperre, "Require all denied\n<IfModule !mod_authz_core.c>\n  Deny from all\n</IfModule>\n");
    }
}

function geheimnis(): string {
    $datei = DATEN_ORDNER . '/geheim.txt';
    if (!is_file($datei)) {
        file_put_contents($datei, bin2hex(random_bytes(32)), LOCK_EX);
    }
    return trim((string) file_get_contents($datei));
}

/** Liest und schreibt die Daten unter einer Dateisperre. */
function mit_daten(callable $aendern) {
    $sperre = fopen(DATEN_ORDNER . '/sperre', 'c');
    if (!$sperre || !flock($sperre, LOCK_EX)) {
        fehler('Speicher belegt', 503);
    }
    $datei = DATEN_ORDNER . '/daten.json';
    $daten = is_file($datei) ? json_decode((string) file_get_contents($datei), true) : null;
    if (!is_array($daten)) {
        $daten = ['rekorde' => [], 'benutzt' => []];
    }
    $ergebnis = $aendern($daten);
    $tmp = $datei . '.tmp';
    file_put_contents($tmp, json_encode($daten, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    rename($tmp, $datei);
    flock($sperre, LOCK_UN);
    fclose($sperre);
    return $ergebnis;
}

function nur_lesen(): array {
    $datei = DATEN_ORDNER . '/daten.json';
    $daten = is_file($datei) ? json_decode((string) file_get_contents($datei), true) : null;
    return is_array($daten) ? ($daten['rekorde'] ?? []) : [];
}

function kategorie_pruefen(string $kategorie): int {
    if (!preg_match('~^([A-Za-z]+)/(\d+)s$~', $kategorie, $m) || !in_array($m[1], STUFEN, true)
        || !in_array((int) $m[2], ZEITEN, true)) {
        fehler('Unbekannte Kategorie');
    }
    return (int) $m[2];
}

function name_pruefen(string $name): string {
    $name = trim(preg_replace('~\s+~u', ' ', $name) ?? '');
    if (!preg_match('~^[\p{L}\p{N} ._\-!?]{1,20}$~u', $name)) {
        fehler('Name: 1 bis 20 Zeichen, Buchstaben, Ziffern, Leerzeichen und . _ - ! ?');
    }
    return $name;
}

ordner();
$methode = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($methode === 'GET') {
    antwort(['ok' => true, 'rekorde' => (object) nur_lesen()]);
}
if ($methode !== 'POST') {
    fehler('Nur GET und POST', 405);
}

$aktion = (string) ($_POST['aktion'] ?? '');
$kategorie = (string) ($_POST['kategorie'] ?? '');
$sekunden = kategorie_pruefen($kategorie);

if ($aktion === 'start') {
    $inhalt = $kategorie . '|' . time() . '|' . bin2hex(random_bytes(8));
    $marke = base64_encode($inhalt) . '.' . hash_hmac('sha256', $inhalt, geheimnis());
    antwort(['ok' => true, 'marke' => $marke]);
}

if ($aktion !== 'eintragen') {
    fehler('Unbekannte Aktion');
}

// --- Marke pruefen -------------------------------------------------------------
$teile = explode('.', (string) ($_POST['marke'] ?? ''));
$inhalt = count($teile) === 2 ? base64_decode($teile[0], true) : false;
if ($inhalt === false || !hash_equals(hash_hmac('sha256', $inhalt, geheimnis()), $teile[1])) {
    fehler('Ungueltige Spielmarke', 403);
}
[$marken_kategorie, $beginn] = explode('|', $inhalt) + ['', '0'];
$alter = time() - (int) $beginn;
if ($marken_kategorie !== $kategorie) {
    fehler('Spielmarke passt nicht zur Kategorie', 403);
}
if ($alter < $sekunden - 3) {
    fehler('Das Spiel ist noch nicht vorbei', 403);
}
if ($alter > $sekunden + 900) {
    fehler('Die Spielmarke ist abgelaufen', 403);
}

// --- Punkte und Name -------------------------------------------------------------
$punkte = filter_var($_POST['punkte'] ?? '', FILTER_VALIDATE_INT);
if ($punkte === false || $punkte < 1 || $punkte > $sekunden * PUNKTE_JE_SEKUNDE) {
    fehler('Unglaubwuerdige Punktzahl');
}
$name = name_pruefen((string) ($_POST['name'] ?? ''));

// --- Eintragen ----------------------------------------------------------------------
$ergebnis = mit_daten(function (array &$daten) use ($kategorie, $punkte, $name, $teile, $beginn) {
    // Benutzte Marken einen Tag lang merken, damit jede nur einmal zaehlt
    $jetzt = time();
    $daten['benutzt'] = array_filter($daten['benutzt'] ?? [], fn ($zeit) => $zeit > $jetzt - 86400);
    $kennung = substr($teile[1], 0, 32);
    if (isset($daten['benutzt'][$kennung])) {
        return ['ok' => false, 'fehler' => 'Diese Partie ist schon eingetragen'];
    }
    $alt = $daten['rekorde'][$kategorie] ?? null;
    if ($alt !== null && $punkte <= $alt['punkte']) {
        return ['ok' => false, 'fehler' => 'Kein neuer Rekord', 'rekorde' => (object) $daten['rekorde']];
    }
    $daten['benutzt'][$kennung] = $jetzt;
    $verlauf = $alt === null ? [] : array_merge(
        [['name' => $alt['name'], 'punkte' => $alt['punkte'], 'datum' => $alt['datum']]],
        $alt['verlauf'] ?? []
    );
    $daten['rekorde'][$kategorie] = [
        'name' => $name,
        'punkte' => $punkte,
        'datum' => date('Y-m-d'),
        'verlauf' => array_slice($verlauf, 0, VERLAUF),
    ];
    return ['ok' => true, 'rekorde' => (object) $daten['rekorde']];
});
antwort($ergebnis, $ergebnis['ok'] ? 200 : 409);
