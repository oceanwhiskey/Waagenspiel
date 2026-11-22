<?php
// Raetsel aus der Datenbank und anonyme Statistik je Raetsel.
//
//   GET  raetsel.php?stufe=2&anzahl=20      -> {"raetsel": [{"id": 17, "s": ["b + c < a", ...]}, ...]}
//        Zufaellig aus allen Raetseln der Stufe (1-4); leer, wenn noch keine eingespielt sind.
//   POST raetsel.php  aktion=antwort        -> {}
//        Felder: id, modus (zeit|ueben), richtig (0|1), ms (Bedenkzeit in Millisekunden)
//
// Gespeichert werden nur Zaehler je Raetsel und Modus (gespielt, richtig, Summe der
// Bedenkzeit). Nichts davon laesst sich einer Person oder einem Geraet zuordnen.

declare(strict_types=1);
require __DIR__ . '/inc/gemeinsam.php';

const HOECHSTENS = 50;          // Raetsel je Abruf
const LAENGSTE_MS = 600000;     // laengere Bedenkzeiten zaehlen als 10 Minuten

$pdo = db();

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'GET') {
    $stufe = (int) ($_GET['stufe'] ?? 0);
    $anzahl = max(1, min(HOECHSTENS, (int) ($_GET['anzahl'] ?? 10)));
    if ($stufe < 1 || $stufe > 4) {
        fehler('Unbekannte Stufe');
    }
    $stmt = $pdo->prepare('SELECT MAX(nr) FROM ' . t('raetsel') . ' WHERE stufe = ?');
    $stmt->execute([$stufe]);
    $hoechste = (int) $stmt->fetchColumn();
    if ($hoechste === 0) {
        antwort(['raetsel' => []]);
    }
    $nummern = [];
    while (count($nummern) < min($anzahl, $hoechste)) {
        $nummern[random_int(1, $hoechste)] = true;
    }
    $platz = implode(',', array_fill(0, count($nummern), '?'));
    $stmt = $pdo->prepare('SELECT id, waagen FROM ' . t('raetsel') . " WHERE stufe = ? AND nr IN ($platz)");
    $stmt->execute(array_merge([$stufe], array_keys($nummern)));
    $raetsel = array_map(fn ($z) => ['id' => (int) $z['id'], 's' => explode('; ', $z['waagen'])], $stmt->fetchAll());
    shuffle($raetsel);
    antwort(['raetsel' => $raetsel]);
}

nur_post();
if (eingabe('aktion') !== 'antwort') {
    fehler('Unbekannte Aktion');
}
$id = filter_var(eingabe('id'), FILTER_VALIDATE_INT, ['options' => ['min_range' => 0]]);
$modus = eingabe('modus');
$richtig = eingabe('richtig');
$ms = filter_var(eingabe('ms'), FILTER_VALIDATE_INT, ['options' => ['min_range' => 0]]);
if ($id === false || !in_array($modus, ['zeit', 'ueben'], true) || !in_array($richtig, ['0', '1'], true) || $ms === false) {
    fehler('Ungültige Antwort');
}
$stmt = $pdo->prepare('SELECT 1 FROM ' . t('raetsel') . ' WHERE id = ?');
$stmt->execute([$id]);
if (!$stmt->fetchColumn()) {
    fehler('Unbekanntes Rätsel', 404);
}
$pdo->prepare('INSERT INTO ' . t('statistik') . ' (raetsel_id, modus, gespielt, richtig, zeit_ms) VALUES (?, ?, 1, ?, ?)
    ON DUPLICATE KEY UPDATE gespielt = gespielt + 1, richtig = richtig + VALUES(richtig), zeit_ms = zeit_ms + VALUES(zeit_ms)')
    ->execute([$id, $modus, (int) $richtig, min($ms, LAENGSTE_MS)]);
antwort([]);
