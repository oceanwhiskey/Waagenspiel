<?php
// Bestenliste mit Spielernamen (docs/04_konzept_mehrspieler.md, Schritt 1).
//
// Je Kategorie (Schwierigkeit/Zeit, z. B. "Mittel/60s") eine Top 10. Jeder
// Spielername steht hoechstens einmal je Kategorie, mit seinem besten Ergebnis.
// Eintragen geht nur mit Spielernamen (Kopf X-Waagenspiel-Schluessel); der Name
// kommt vom Geraet, nicht aus einem Eingabefeld.
//
//   GET  bestenliste.php                       -> {"listen": {kategorie: [{name, punkte, datum}, ...]}}
//   POST bestenliste.php  aktion=start         -> {"marke": "..."}           (beim Spielstart)
//   POST bestenliste.php  aktion=eintragen     -> {"platz", "verbessert", "bestes", "liste"}
//        Felder: marke, kategorie, punkte
//
// Schutz gegen einfaches Schummeln: Die Marke ist signiert, nur einmal gueltig
// und erst nach Ablauf der Spielzeit einloesbar; die Punkte muessen zur
// Spielzeit passen. (Ganz faelschungssicher wird es erst, wenn der Server die
// Raetsel austeilt: Schritt 2 im Konzept.)

declare(strict_types=1);
require __DIR__ . '/inc/gemeinsam.php';

const STUFEN = ['Steigend', 'Leicht', 'Mittel', 'Schwer', 'Profi'];
const ZEITEN = [30, 60, 90, 120];
const PUNKTE_JE_SEKUNDE = 150;  // hoechstens 120 Punkte je Runde (Profi, Serie x3), mindestens ~0,8 s je Runde
const PLAETZE = 10;

function kategorie_pruefen(string $kategorie): int {
    if (!preg_match('~^([A-Za-z]+)/(\d+)s$~', $kategorie, $m) || !in_array($m[1], STUFEN, true)
        || !in_array((int) $m[2], ZEITEN, true)) {
        fehler('Unbekannte Kategorie');
    }
    return (int) $m[2];
}

function liste(string $kategorie): array {
    $stmt = db()->prepare('SELECT s.name, e.punkte, e.erreicht FROM ' . t('ergebnis') . ' e JOIN ' . t('spieler')
        . ' s ON s.id = e.spieler_id WHERE e.kategorie = ? ORDER BY e.punkte DESC, e.erreicht ASC LIMIT ' . PLAETZE);
    $stmt->execute([$kategorie]);
    return array_map(fn ($z) => ['name' => $z['name'], 'punkte' => (int) $z['punkte'], 'datum' => substr($z['erreicht'], 0, 10)],
        $stmt->fetchAll());
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
    spieler(); // mit Schluessel: zaehlt als Benutzung, der Name bleibt reserviert
    $inhalt = $kategorie . '|' . time() . '|' . bin2hex(random_bytes(8));
    antwort(['marke' => base64_encode($inhalt) . '.' . hash_hmac('sha256', $inhalt, geheimnis())]);
}
if ($aktion !== 'eintragen') {
    fehler('Unbekannte Aktion');
}

$spieler = spieler_noetig();

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

// --- Eintragen ---------------------------------------------------------------------------------
$kennung = substr($teile[1], 0, 32);
$pdo->prepare('DELETE FROM ' . t('marke') . ' WHERE benutzt < ?')->execute([gmdate('Y-m-d H:i:s', time() - 86400)]);
try {
    $pdo->prepare('INSERT INTO ' . t('marke') . ' (kennung, benutzt) VALUES (?, ?)')->execute([$kennung, jetzt()]);
} catch (PDOException $e) {
    fehler('Diese Partie ist schon eingetragen', 409);
}

$stmt = $pdo->prepare('SELECT punkte FROM ' . t('ergebnis') . ' WHERE spieler_id = ? AND kategorie = ?');
$stmt->execute([$spieler['id'], $kategorie]);
$bisher = $stmt->fetchColumn();
$verbessert = $bisher === false || $punkte > (int) $bisher;
if ($verbessert) {
    $pdo->prepare('INSERT INTO ' . t('ergebnis') . ' (spieler_id, kategorie, punkte, erreicht) VALUES (?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE punkte = VALUES(punkte), erreicht = VALUES(erreicht)')
        ->execute([$spieler['id'], $kategorie, $punkte, jetzt()]);
}

// Platz dieses Spielers (mit seinem besten Ergebnis) in der Kategorie
$stmt = $pdo->prepare('SELECT punkte, erreicht FROM ' . t('ergebnis') . ' WHERE spieler_id = ? AND kategorie = ?');
$stmt->execute([$spieler['id'], $kategorie]);
$bestes = $stmt->fetch();
$stmt = $pdo->prepare('SELECT COUNT(*) FROM ' . t('ergebnis') . ' WHERE kategorie = ? AND (punkte > ? OR (punkte = ? AND erreicht < ?))');
$stmt->execute([$kategorie, $bestes['punkte'], $bestes['punkte'], $bestes['erreicht']]);
$platz = (int) $stmt->fetchColumn() + 1;

antwort([
    'platz' => $platz,
    'verbessert' => $verbessert,
    'bestes' => (int) $bestes['punkte'],
    'liste' => liste($kategorie),
]);
