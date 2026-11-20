<?php
// Bestenliste als Rekord-Historie.
//
// Je Kategorie (Schwierigkeit/Zeit, z. B. "Mittel/60s") werden alle Rekorde
// aufgehoben: Wer den bisherigen Rekord bricht, traegt sich mit einem frei
// gewaehlten Namen ein, und der alte Rekord bleibt darunter stehen. Es gibt keine
// Anmeldung und keine Spielerkonten.
//
//   GET  bestenliste.php                     -> {"listen": {kategorie: [{name, punkte, datum}, ...]}}
//                                               (hoechster = aktueller Rekord zuerst)
//   POST bestenliste.php  aktion=start       -> {"marke": "..."}           (beim Spielstart)
//   POST bestenliste.php  aktion=eintragen   -> {"liste": [...]}
//        Felder: marke, kategorie, punkte, name
//        Kein Rekord (mehr): 409 mit "rekord" (aktueller Rekord).
//
// Schutz gegen einfaches Schummeln: Die Marke ist signiert, nur einmal gueltig
// und erst nach Ablauf der Spielzeit einloesbar; die Punkte muessen zur
// Spielzeit passen. (Ganz faelschungssicher waere es erst, wenn der Server die
// Raetsel austeilt.)

declare(strict_types=1);
require __DIR__ . '/inc/gemeinsam.php';

const STUFEN = ['Steigend', 'Leicht', 'Mittel', 'Schwer', 'Profi'];
const ZEITEN = [30, 60, 90, 120];
const PUNKTE_JE_SEKUNDE = 150;  // hoechstens 120 Punkte je Runde (Profi, Serie x3), mindestens ~0,8 s je Runde
const HISTORIE = 50;            // so viele Rekorde je Kategorie werden angezeigt

function kategorie_pruefen(string $kategorie): int {
    if (!preg_match('~^([A-Za-z]+)/(\d+)s$~', $kategorie, $m) || !in_array($m[1], STUFEN, true)
        || !in_array((int) $m[2], ZEITEN, true)) {
        fehler('Unbekannte Kategorie');
    }
    return (int) $m[2];
}

function liste(string $kategorie): array {
    $stmt = db()->prepare('SELECT name, punkte, erreicht FROM ' . t('rekord')
        . ' WHERE kategorie = ? ORDER BY punkte DESC, erreicht ASC LIMIT ' . HISTORIE);
    $stmt->execute([$kategorie]);
    return array_map(fn ($z) => ['name' => $z['name'], 'punkte' => (int) $z['punkte'], 'datum' => substr($z['erreicht'], 0, 10)],
        $stmt->fetchAll());
}

function rekord(string $kategorie): int {
    $stmt = db()->prepare('SELECT MAX(punkte) FROM ' . t('rekord') . ' WHERE kategorie = ?');
    $stmt->execute([$kategorie]);
    return (int) $stmt->fetchColumn();
}

$methode = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$pdo = db();

if ($methode === 'GET') {
    $listen = [];
    foreach (STUFEN as $stufe) {
        foreach (ZEITEN as $zeit) {
            $liste = liste("$stufe/{$zeit}s");
            if ($liste) {
                $listen["$stufe/{$zeit}s"] = $liste;
            }
        }
    }
    antwort(['listen' => (object) $listen]);
}

nur_post();
$aktion = eingabe('aktion');
$kategorie = eingabe('kategorie');
$sekunden = kategorie_pruefen($kategorie);

if ($aktion === 'start') {
    $inhalt = $kategorie . '|' . time() . '|' . bin2hex(random_bytes(8));
    antwort(['marke' => base64_encode($inhalt) . '.' . hash_hmac('sha256', $inhalt, geheimnis())]);
}
if ($aktion !== 'eintragen') {
    fehler('Unbekannte Aktion');
}

// --- Marke pruefen -------------------------------------------------------------------------
$teile = explode('.', eingabe('marke'));
$inhalt = count($teile) === 2 ? base64_decode($teile[0], true) : false;
if ($inhalt === false || !hash_equals(hash_hmac('sha256', $inhalt, geheimnis()), $teile[1])) {
    fehler('Ungültige Spielmarke', 403);
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
$punkte = filter_var(eingabe('punkte'), FILTER_VALIDATE_INT);
if ($punkte === false || $punkte < 1 || $punkte > $sekunden * PUNKTE_JE_SEKUNDE) {
    fehler('Unglaubwürdige Punktzahl');
}
$name = name_pruefen(eingabe('name'));

// --- Eintragen ---------------------------------------------------------------------------------
// Zwei gleichzeitige Rekorde werden nacheinander geprueft. Die Sperre endet spaetestens mit der
// Verbindung, also auch, wenn fehler() das Skript vorher beendet.
$pdo->query('SELECT GET_LOCK(' . $pdo->quote(t('rekord')) . ', 5)')->fetchColumn();
$bisher = rekord($kategorie);
if ($punkte <= $bisher) {
    fehler('Inzwischen gibt es einen höheren Rekord: ' . $bisher . ' Punkte.', 409, ['rekord' => $bisher]);
}
$kennung = substr($teile[1], 0, 32);
$pdo->prepare('DELETE FROM ' . t('marke') . ' WHERE benutzt < ?')->execute([gmdate('Y-m-d H:i:s', time() - 86400)]);
try {
    $pdo->prepare('INSERT INTO ' . t('marke') . ' (kennung, benutzt) VALUES (?, ?)')->execute([$kennung, jetzt()]);
} catch (PDOException $e) {
    fehler('Diese Partie ist schon eingetragen', 409);
}
$pdo->prepare('INSERT INTO ' . t('rekord') . ' (kategorie, name, punkte, erreicht) VALUES (?, ?, ?, ?)')
    ->execute([$kategorie, $name, $punkte, jetzt()]);
$pdo->query('SELECT RELEASE_LOCK(' . $pdo->quote(t('rekord')) . ')')->fetchColumn();

antwort(['liste' => liste($kategorie)]);
