<?php
// Verwaltung: Raetsel einspielen, Sicherung holen und zurueckspielen.
// Jeder Aufruf braucht den Kopf X-Waagenspiel-Verwaltung mit dem Schluessel aus
// waagenspiel-config/verwaltung.txt. Benutzt wird das von werkzeuge/datenbank.py.
//
//   POST aktion=import_beginnen                      -> {}  (leere Tabelle raetsel_neu)
//   POST aktion=import_teil   zeilen=<TSV>           -> {"neu": n}
//        je Zeile: id <TAB> stufe <TAB> nr <TAB> abkuerzung <TAB> waagen
//   POST aktion=import_abschliessen  anzahl=<n>      -> {"anzahl": n}
//        prueft die Anzahl und tauscht raetsel_neu gegen raetsel (das Spiel laeuft weiter)
//   POST aktion=sicherung                            -> {"erstellt", "raetsel", "rekord": [...], "statistik": [...]}
//   POST aktion=wiederherstellen  tabelle=rekord|statistik  leeren=0|1  zeilen=<JSON-Liste>  -> {"neu": n}

declare(strict_types=1);
require __DIR__ . '/inc/gemeinsam.php';

nur_post();
verwaltung_pruefen();
$pdo = db();
$aktion = eingabe('aktion');

const SPALTEN = [
    'rekord' => ['id', 'kategorie', 'name', 'punkte', 'erreicht'],
    'statistik' => ['raetsel_id', 'modus', 'gespielt', 'richtig', 'zeit_ms'],
];

/** Fuegt Zeilen (Listen in Spaltenreihenfolge) in Portionen ein. */
function einfuegen(PDO $pdo, string $tabelle, array $spalten, array $zeilen): void {
    foreach (array_chunk($zeilen, 500) as $teil) {
        $platz = '(' . implode(',', array_fill(0, count($spalten), '?')) . ')';
        $sql = "INSERT INTO $tabelle (" . implode(',', $spalten) . ') VALUES '
            . implode(',', array_fill(0, count($teil), $platz));
        $pdo->prepare($sql)->execute(array_merge(...$teil));
    }
}

switch ($aktion) {
    case 'import_beginnen':
        $pdo->exec('DROP TABLE IF EXISTS ' . t('raetsel_neu'));
        raetsel_tabelle_anlegen($pdo, t('raetsel_neu'));
        antwort([]);

    case 'import_teil':
        $zeilen = [];
        foreach (preg_split('~\R~', trim($_POST['zeilen'] ?? '')) as $zeile) {
            $f = explode("\t", $zeile);
            if (count($f) !== 5 || !ctype_digit($f[0]) || !in_array($f[1], ['1', '2', '3', '4'], true)
                || !ctype_digit($f[2]) || !in_array($f[3], ['0', '1'], true)
                || !preg_match('~^[0-9abcd +<=;]{5,120}$~', $f[4])) {
                fehler('Ungültige Zeile: ' . substr($zeile, 0, 80));
            }
            $zeilen[] = [(int) $f[0], (int) $f[1], (int) $f[2], (int) $f[3], $f[4]];
        }
        einfuegen($pdo, t('raetsel_neu'), ['id', 'stufe', 'nr', 'abkuerzung', 'waagen'], $zeilen);
        antwort(['neu' => count($zeilen)]);

    case 'import_abschliessen':
        $anzahl = (int) $pdo->query('SELECT COUNT(*) FROM ' . t('raetsel_neu'))->fetchColumn();
        if ($anzahl !== (int) eingabe('anzahl')) {
            fehler("Anzahl stimmt nicht: $anzahl in der Datenbank");
        }
        $pdo->exec('DROP TABLE IF EXISTS ' . t('raetsel_alt'));
        $pdo->exec('RENAME TABLE ' . t('raetsel') . ' TO ' . t('raetsel_alt') . ', ' . t('raetsel_neu') . ' TO ' . t('raetsel'));
        $pdo->exec('DROP TABLE ' . t('raetsel_alt'));
        antwort(['anzahl' => $anzahl]);

    case 'sicherung':
        $daten = ['erstellt' => gmdate('Y-m-d\TH:i:s\Z')];
        $daten['raetsel'] = (int) $pdo->query('SELECT COUNT(*) FROM ' . t('raetsel'))->fetchColumn();
        foreach (SPALTEN as $tabelle => $spalten) {
            $daten[$tabelle . '_spalten'] = $spalten;
            $daten[$tabelle] = $pdo->query('SELECT ' . implode(',', $spalten) . ' FROM ' . t($tabelle))->fetchAll(PDO::FETCH_NUM);
        }
        antwort($daten);

    case 'wiederherstellen':
        $tabelle = eingabe('tabelle');
        if (!isset(SPALTEN[$tabelle])) {
            fehler('Unbekannte Tabelle');
        }
        $zeilen = json_decode((string) ($_POST['zeilen'] ?? ''), true);
        if (!is_array($zeilen)) {
            fehler('Zeilen fehlen');
        }
        foreach ($zeilen as $z) {
            if (!is_array($z) || count($z) !== count(SPALTEN[$tabelle])) {
                fehler('Ungültige Zeile');
            }
        }
        $pdo->beginTransaction();
        if (eingabe('leeren') === '1') {
            $pdo->exec('DELETE FROM ' . t($tabelle));
        }
        einfuegen($pdo, t($tabelle), SPALTEN[$tabelle], $zeilen);
        $pdo->commit();
        antwort(['neu' => count($zeilen)]);

    default:
        fehler('Unbekannte Aktion');
}
