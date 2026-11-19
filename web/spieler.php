<?php
// Spielername ohne Passwort (docs/04_konzept_mehrspieler.md, Abschnitt 2).
//
// Ein Name gehoert dem Geraet, das ihn zuletzt benutzt hat. Wird er einen Tag
// lang nicht benutzt, ist er wieder frei: Dann kann ihn jedes Geraet nehmen
// (z. B. das zweite Geraet desselben Spielers) und spielt mit seinen Ergebnissen
// weiter. Ein Uebertragungscode ist dafuer nicht noetig.
//
// POST aktion=nehmen     name   -> {name, schluessel}   (schluessel null: Name war schon der eigene)
// POST aktion=ich               -> {name}
// POST aktion=abmelden          -> {}   (dieses Geraet; der Name bleibt mit Ergebnissen bestehen)
// POST aktion=loeschen          -> {}   (Name und alle Ergebnisse)
//
// Alle Aktionen ausser "nehmen" brauchen den Kopf X-Waagenspiel-Schluessel.

declare(strict_types=1);
require __DIR__ . '/inc/gemeinsam.php';

const NEUE_NAMEN_JE_STUNDE = 30;

nur_post();
$aktion = eingabe('aktion');
$pdo = db();

switch ($aktion) {
    case 'nehmen':
    case 'anlegen': // alter Name der Aktion
        $name = name_pruefen(eingabe('name'));
        $ich = spieler();
        $stmt = $pdo->prepare('SELECT id, name, zuletzt FROM ' . t('spieler') . ' WHERE name_klein = ?');
        $stmt->execute([klein($name)]);
        $vorhanden = $stmt->fetch() ?: null;
        if ($vorhanden && $ich && (int) $vorhanden['id'] === (int) $ich['id']) {
            antwort(['name' => $vorhanden['name'], 'schluessel' => null]);
        }
        if ($vorhanden) {
            $frei_ab = strtotime($vorhanden['zuletzt'] . ' UTC') + NAME_GESPERRT_S;
            if ($frei_ab > time()) {
                fehler('„' . $vorhanden['name'] . '“ ist gerade vergeben.', 409, ['frei_ab' => gmdate('Y-m-d\TH:i:s\Z', $frei_ab)]);
            }
        } else {
            $stmt = $pdo->prepare('SELECT COUNT(*) FROM ' . t('spieler') . ' WHERE erstellt > ?');
            $stmt->execute([gmdate('Y-m-d H:i:s', time() - 3600)]);
            if ((int) $stmt->fetchColumn() >= NEUE_NAMEN_JE_STUNDE) {
                fehler('Gerade werden sehr viele Namen angelegt. Bitte später noch einmal.', 429);
            }
        }
        try {
            $pdo->beginTransaction();
            if ($ich) { // dieses Geraet laesst seinen bisherigen Namen los
                $pdo->prepare('DELETE FROM ' . t('geraet') . ' WHERE id = ?')->execute([$ich['geraet_id']]);
            }
            if ($vorhanden) { // freier Name: alte Geraete verlieren ihn, die Ergebnisse bleiben
                $id = (int) $vorhanden['id'];
                $name = $vorhanden['name'];
                $pdo->prepare('DELETE FROM ' . t('geraet') . ' WHERE spieler_id = ?')->execute([$id]);
                $pdo->prepare('UPDATE ' . t('spieler') . ' SET zuletzt = ? WHERE id = ?')->execute([jetzt(), $id]);
            } else {
                $pdo->prepare('INSERT INTO ' . t('spieler') . ' (name, name_klein, erstellt, zuletzt) VALUES (?, ?, ?, ?)')
                    ->execute([$name, klein($name), jetzt(), jetzt()]);
                $id = (int) $pdo->lastInsertId();
            }
            $schluessel = geraet_anlegen($id);
            $pdo->commit();
        } catch (PDOException $e) {
            $pdo->rollBack();
            fehler('„' . $name . '“ ist gerade vergeben.', 409);
        }
        antwort(['name' => $name, 'schluessel' => $schluessel]);

    case 'ich':
        $s = spieler_noetig();
        antwort(['name' => $s['name']]);

    case 'abmelden':
        $s = spieler_noetig();
        $pdo->prepare('DELETE FROM ' . t('geraet') . ' WHERE id = ?')->execute([$s['geraet_id']]);
        antwort([]);

    case 'loeschen':
        $s = spieler_noetig();
        $pdo->prepare('DELETE FROM ' . t('spieler') . ' WHERE id = ?')->execute([$s['id']]);
        antwort([]);

    default:
        fehler('Unbekannte Aktion');
}
