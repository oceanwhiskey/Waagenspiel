<?php
// Gemeinsame Bausteine fuer spieler.php und bestenliste.php (docs/04, Schritt 1).
//
// - Datenbank: Zugangsdaten aus waagenspiel-config/db.ini, die AUSSERHALB der
//   Webseiten liegt (wird von hier aus nach oben gesucht). Tabellen werden beim
//   ersten Aufruf angelegt.
// - Spieler: Ein Geraet weist sich mit dem Kopf "X-Waagenspiel-Schluessel" aus.
//   Gespeichert wird nur der SHA-256-Hash des zufaelligen Schluessels.
// - Kein Passwort, keine E-Mail, keine IP-Adressen.

declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

const NAME_MUSTER = '~^[\p{L}\p{N} ._\-!?]{1,20}$~u';

function antwort(array $daten, int $status = 200): void {
    http_response_code($status);
    echo json_encode($daten + ['ok' => true], JSON_UNESCAPED_UNICODE);
    exit;
}

function fehler(string $text, int $status = 400): void {
    http_response_code($status);
    echo json_encode(['ok' => false, 'fehler' => $text], JSON_UNESCAPED_UNICODE);
    exit;
}

function eingabe(string $feld): string {
    return trim((string) ($_POST[$feld] ?? ''));
}

function nur_post(): void {
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
        fehler('Nur POST', 405);
    }
}

// --- Datenbank ---------------------------------------------------------------------

function konfig_datei(): string {
    $ordner = __DIR__;
    for ($i = 0; $i < 8; $i++) {
        $kandidat = $ordner . '/waagenspiel-config/db.ini';
        if (is_readable($kandidat)) {
            return $kandidat;
        }
        $ordner = dirname($ordner);
    }
    fehler('Datenbank nicht eingerichtet', 500);
}

/** Tabellenpraefix; eine Datei praefix.txt neben dieser Datei aendert es (fuer Tests). */
function t(string $name): string {
    static $praefix = null;
    if ($praefix === null) {
        $datei = __DIR__ . '/praefix.txt';
        $praefix = is_readable($datei) ? preg_replace('~[^a-z_]~', '', trim((string) file_get_contents($datei))) : 'ws_';
    }
    return $praefix . $name;
}

function db(): PDO {
    static $pdo = null;
    if ($pdo !== null) {
        return $pdo;
    }
    $c = parse_ini_file(konfig_datei(), true);
    $d = $c['datenbank'] ?? null;
    if (!$d) {
        fehler('Datenbank nicht eingerichtet', 500);
    }
    try {
        $pdo = new PDO(
            "mysql:host={$d['host']};port=" . (int) ($d['port'] ?? 3306) . ";dbname={$d['name']};charset=utf8mb4",
            $d['benutzer'], $d['passwort'],
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
             PDO::ATTR_EMULATE_PREPARES => false]
        );
    } catch (PDOException $e) {
        fehler('Datenbank nicht erreichbar', 503);
    }
    $pdo->exec("SET time_zone = '+00:00'");
    tabellen_anlegen($pdo);
    return $pdo;
}

function tabellen_anlegen(PDO $pdo): void {
    $opt = 'ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci';
    $pdo->exec('CREATE TABLE IF NOT EXISTS ' . t('spieler') . " (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(20) NOT NULL,
        name_klein VARCHAR(20) NOT NULL,
        erstellt DATETIME NOT NULL,
        zuletzt DATETIME NOT NULL,
        UNIQUE KEY name_klein (name_klein)
    ) $opt");
    $pdo->exec('CREATE TABLE IF NOT EXISTS ' . t('geraet') . " (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        spieler_id INT UNSIGNED NOT NULL,
        schluessel_hash CHAR(64) NOT NULL,
        erstellt DATETIME NOT NULL,
        zuletzt DATETIME NOT NULL,
        UNIQUE KEY schluessel_hash (schluessel_hash),
        FOREIGN KEY (spieler_id) REFERENCES " . t('spieler') . "(id) ON DELETE CASCADE
    ) $opt");
    $pdo->exec('CREATE TABLE IF NOT EXISTS ' . t('uebertragung') . " (
        code_hash CHAR(64) PRIMARY KEY,
        spieler_id INT UNSIGNED NOT NULL,
        ablauf DATETIME NOT NULL,
        FOREIGN KEY (spieler_id) REFERENCES " . t('spieler') . "(id) ON DELETE CASCADE
    ) $opt");
    $pdo->exec('CREATE TABLE IF NOT EXISTS ' . t('ergebnis') . " (
        spieler_id INT UNSIGNED NOT NULL,
        kategorie VARCHAR(20) NOT NULL,
        punkte INT NOT NULL,
        erreicht DATETIME NOT NULL,
        PRIMARY KEY (spieler_id, kategorie),
        KEY rangliste (kategorie, punkte),
        FOREIGN KEY (spieler_id) REFERENCES " . t('spieler') . "(id) ON DELETE CASCADE
    ) $opt");
    $pdo->exec('CREATE TABLE IF NOT EXISTS ' . t('marke') . " (
        kennung CHAR(32) PRIMARY KEY,
        benutzt DATETIME NOT NULL
    ) $opt");
    $pdo->exec('CREATE TABLE IF NOT EXISTS ' . t('fehlversuch') . " (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        art VARCHAR(20) NOT NULL,
        zeit DATETIME NOT NULL,
        KEY art_zeit (art, zeit)
    ) $opt");
    $pdo->exec('CREATE TABLE IF NOT EXISTS ' . t('einstellung') . " (
        schluessel VARCHAR(40) PRIMARY KEY,
        wert TEXT NOT NULL
    ) $opt");
}

function jetzt(): string {
    return gmdate('Y-m-d H:i:s');
}

/** Geheimnis fuer signierte Spielmarken; entsteht beim ersten Bedarf in der Datenbank. */
function geheimnis(): string {
    $pdo = db();
    $wert = $pdo->query('SELECT wert FROM ' . t('einstellung') . " WHERE schluessel = 'marken_geheimnis'")->fetchColumn();
    if ($wert) {
        return (string) $wert;
    }
    $neu = bin2hex(random_bytes(32));
    $pdo->prepare('INSERT IGNORE INTO ' . t('einstellung') . " (schluessel, wert) VALUES ('marken_geheimnis', ?)")->execute([$neu]);
    return (string) $pdo->query('SELECT wert FROM ' . t('einstellung') . " WHERE schluessel = 'marken_geheimnis'")->fetchColumn();
}

// --- Fehlversuche (gegen Durchprobieren) ----------------------------------------------

function zu_viele(string $art, int $hoechstens, int $sekunden): bool {
    $stmt = db()->prepare('SELECT COUNT(*) FROM ' . t('fehlversuch') . ' WHERE art = ? AND zeit > ?');
    $stmt->execute([$art, gmdate('Y-m-d H:i:s', time() - $sekunden)]);
    return (int) $stmt->fetchColumn() >= $hoechstens;
}

function versuch_merken(string $art): void {
    $pdo = db();
    $pdo->prepare('INSERT INTO ' . t('fehlversuch') . ' (art, zeit) VALUES (?, ?)')->execute([$art, jetzt()]);
    $pdo->prepare('DELETE FROM ' . t('fehlversuch') . ' WHERE zeit < ?')->execute([gmdate('Y-m-d H:i:s', time() - 86400)]);
}

// --- Spieler -------------------------------------------------------------------------------

function name_pruefen(string $name): string {
    $name = trim(preg_replace('~\s+~u', ' ', $name) ?? '');
    if (!preg_match(NAME_MUSTER, $name)) {
        fehler('Name: 1 bis 20 Zeichen, Buchstaben, Ziffern, Leerzeichen und . _ - ! ?');
    }
    return $name;
}

function klein(string $name): string {
    return function_exists('mb_strtolower') ? mb_strtolower($name, 'UTF-8') : strtolower($name);
}

function neuer_schluessel(): string {
    return rtrim(strtr(base64_encode(random_bytes(32)), '+/', '-_'), '=');
}

function schluessel_hash(string $schluessel): string {
    return hash('sha256', $schluessel);
}

/** Neues Geraet fuer einen Spieler; liefert den Schluessel (nur dieses eine Mal im Klartext). */
function geraet_anlegen(int $spieler_id): string {
    $schluessel = neuer_schluessel();
    db()->prepare('INSERT INTO ' . t('geraet') . ' (spieler_id, schluessel_hash, erstellt, zuletzt) VALUES (?, ?, ?, ?)')
        ->execute([$spieler_id, schluessel_hash($schluessel), jetzt(), jetzt()]);
    return $schluessel;
}

/** Der angemeldete Spieler oder null. Liest den Kopf X-Waagenspiel-Schluessel. */
function spieler(): ?array {
    static $gelesen = false, $spieler = null;
    if ($gelesen) {
        return $spieler;
    }
    $gelesen = true;
    $schluessel = (string) ($_SERVER['HTTP_X_WAAGENSPIEL_SCHLUESSEL'] ?? '');
    if ($schluessel === '' || strlen($schluessel) > 100) {
        return null;
    }
    $stmt = db()->prepare('SELECT s.id, s.name, s.erstellt, g.id AS geraet_id FROM ' . t('geraet') . ' g JOIN '
        . t('spieler') . ' s ON s.id = g.spieler_id WHERE g.schluessel_hash = ?');
    $stmt->execute([schluessel_hash($schluessel)]);
    $spieler = $stmt->fetch() ?: null;
    if ($spieler) {
        $pdo = db();
        $pdo->prepare('UPDATE ' . t('geraet') . ' SET zuletzt = ? WHERE id = ?')->execute([jetzt(), $spieler['geraet_id']]);
        $pdo->prepare('UPDATE ' . t('spieler') . ' SET zuletzt = ? WHERE id = ?')->execute([jetzt(), $spieler['id']]);
    }
    return $spieler;
}

function spieler_noetig(): array {
    $spieler = spieler();
    if (!$spieler) {
        fehler('Dieses Geraet hat keinen Spielernamen (mehr).', 401);
    }
    return $spieler;
}
