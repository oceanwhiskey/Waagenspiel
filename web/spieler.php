<?php
// Spielername und Geraeteschluessel (docs/04_konzept_mehrspieler.md, Abschnitt 2).
//
// POST aktion=anlegen        name          -> {name, schluessel}
// POST aktion=ich                          -> {name, erstellt, geraete: [...]}
// POST aktion=umbenennen     name          -> {name}
// POST aktion=code_erzeugen                -> {code, gueltig_s}
// POST aktion=code_einloesen code          -> {name, schluessel}
// POST aktion=geraet_abmelden id           -> {}
// POST aktion=abmelden                     -> {name_geloescht}  (dieses Geraet; letztes -> Name weg)
// POST aktion=loeschen                     -> {}   (Name und alle Ergebnisse)
//
// Alle Aktionen ausser "anlegen" und "code_einloesen" brauchen den Kopf
// X-Waagenspiel-Schluessel.

declare(strict_types=1);
require __DIR__ . '/inc/gemeinsam.php';

const NEUE_NAMEN_JE_STUNDE = 30;
const CODE_GUELTIG_S = 600;
const CODE_ZEICHEN = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // ohne 0/O und 1/I

nur_post();
$aktion = eingabe('aktion');
$pdo = db();

function name_frei(string $name, ?int $ausser = null): bool {
    $stmt = db()->prepare('SELECT id FROM ' . t('spieler') . ' WHERE name_klein = ?');
    $stmt->execute([klein($name)]);
    $id = $stmt->fetchColumn();
    return $id === false || ($ausser !== null && (int) $id === $ausser);
}

function code_normal(string $code): string {
    $code = strtoupper(preg_replace('~[^A-Za-z0-9]~', '', $code) ?? '');
    return preg_replace('~^WAAGE~', '', $code) ?? '';
}

switch ($aktion) {
    case 'anlegen':
        $name = name_pruefen(eingabe('name'));
        $stmt = $pdo->prepare('SELECT COUNT(*) FROM ' . t('spieler') . ' WHERE erstellt > ?');
        $stmt->execute([gmdate('Y-m-d H:i:s', time() - 3600)]);
        if ((int) $stmt->fetchColumn() >= NEUE_NAMEN_JE_STUNDE) {
            fehler('Gerade werden sehr viele Namen angelegt. Bitte spaeter noch einmal.', 429);
        }
        if (!name_frei($name)) {
            fehler('Diesen Namen gibt es schon. Bitte einen anderen waehlen.', 409);
        }
        try {
            $pdo->beginTransaction();
            $pdo->prepare('INSERT INTO ' . t('spieler') . ' (name, name_klein, erstellt, zuletzt) VALUES (?, ?, ?, ?)')
                ->execute([$name, klein($name), jetzt(), jetzt()]);
            $schluessel = geraet_anlegen((int) $pdo->lastInsertId());
            $pdo->commit();
        } catch (PDOException $e) {
            $pdo->rollBack();
            fehler('Diesen Namen gibt es schon. Bitte einen anderen waehlen.', 409);
        }
        antwort(['name' => $name, 'schluessel' => $schluessel]);

    case 'ich':
        $s = spieler_noetig();
        $stmt = $pdo->prepare('SELECT id, erstellt, zuletzt FROM ' . t('geraet') . ' WHERE spieler_id = ? ORDER BY erstellt');
        $stmt->execute([$s['id']]);
        $geraete = array_map(fn ($g) => [
            'id' => (int) $g['id'],
            'erstellt' => $g['erstellt'] . 'Z',
            'zuletzt' => $g['zuletzt'] . 'Z',
            'dieses' => (int) $g['id'] === (int) $s['geraet_id'],
        ], $stmt->fetchAll());
        antwort(['name' => $s['name'], 'erstellt' => $s['erstellt'] . 'Z', 'geraete' => $geraete]);

    case 'umbenennen':
        $s = spieler_noetig();
        $name = name_pruefen(eingabe('name'));
        if (!name_frei($name, (int) $s['id'])) {
            fehler('Diesen Namen gibt es schon. Bitte einen anderen waehlen.', 409);
        }
        $pdo->prepare('UPDATE ' . t('spieler') . ' SET name = ?, name_klein = ? WHERE id = ?')
            ->execute([$name, klein($name), $s['id']]);
        antwort(['name' => $name]);

    case 'code_erzeugen':
        $s = spieler_noetig();
        $roh = '';
        for ($i = 0; $i < 8; $i++) {
            $roh .= CODE_ZEICHEN[random_int(0, strlen(CODE_ZEICHEN) - 1)];
        }
        $pdo->prepare('DELETE FROM ' . t('uebertragung') . ' WHERE spieler_id = ? OR ablauf < ?')->execute([$s['id'], jetzt()]);
        $pdo->prepare('INSERT INTO ' . t('uebertragung') . ' (code_hash, spieler_id, ablauf) VALUES (?, ?, ?)')
            ->execute([hash('sha256', $roh), $s['id'], gmdate('Y-m-d H:i:s', time() + CODE_GUELTIG_S)]);
        antwort(['code' => 'WAAGE-' . substr($roh, 0, 4) . '-' . substr($roh, 4), 'gueltig_s' => CODE_GUELTIG_S]);

    case 'code_einloesen':
        if (zu_viele('code', 50, 600)) {
            fehler('Zu viele falsche Codes. Bitte in ein paar Minuten noch einmal.', 429);
        }
        $roh = code_normal(eingabe('code'));
        $stmt = $pdo->prepare('SELECT u.spieler_id, s.name FROM ' . t('uebertragung') . ' u JOIN ' . t('spieler')
            . ' s ON s.id = u.spieler_id WHERE u.code_hash = ? AND u.ablauf >= ?');
        $stmt->execute([hash('sha256', $roh), jetzt()]);
        $treffer = $stmt->fetch();
        if (!$treffer) {
            versuch_merken('code');
            fehler('Diesen Code gibt es nicht oder er ist abgelaufen.', 404);
        }
        $pdo->prepare('DELETE FROM ' . t('uebertragung') . ' WHERE code_hash = ?')->execute([hash('sha256', $roh)]);
        antwort(['name' => $treffer['name'], 'schluessel' => geraet_anlegen((int) $treffer['spieler_id'])]);

    case 'geraet_abmelden': // ein anderes Geraet dieses Spielers
        $s = spieler_noetig();
        $pdo->prepare('DELETE FROM ' . t('geraet') . ' WHERE id = ? AND spieler_id = ? AND id <> ?')
            ->execute([(int) eingabe('id'), $s['id'], $s['geraet_id']]);
        antwort([]);

    case 'abmelden': // dieses Geraet; war es das letzte, verschwindet der Name samt Ergebnissen
        $s = spieler_noetig();
        $pdo->prepare('DELETE FROM ' . t('geraet') . ' WHERE id = ?')->execute([$s['geraet_id']]);
        $stmt = $pdo->prepare('SELECT COUNT(*) FROM ' . t('geraet') . ' WHERE spieler_id = ?');
        $stmt->execute([$s['id']]);
        $geloescht = (int) $stmt->fetchColumn() === 0;
        if ($geloescht) {
            $pdo->prepare('DELETE FROM ' . t('spieler') . ' WHERE id = ?')->execute([$s['id']]);
        }
        antwort(['name_geloescht' => $geloescht]);

    case 'loeschen':
        $s = spieler_noetig();
        $pdo->prepare('DELETE FROM ' . t('spieler') . ' WHERE id = ?')->execute([$s['id']]);
        antwort([]);

    default:
        fehler('Unbekannte Aktion');
}
