<?php
// Gemeinsame Bausteine fuer bestenliste.php, raetsel.php und verwaltung.php.
//
// - Datenbank: Zugangsdaten aus waagenspiel-config/db.ini, die AUSSERHALB der
//   Webseiten liegt (wird von hier aus nach oben gesucht). Tabellen werden beim
//   ersten Aufruf angelegt.
// - Verwaltung (Raetsel einspielen, Sicherung): Schluessel aus
//   waagenspiel-config/verwaltung.txt im selben Ordner.
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

function fehler(string $text, int $status = 400, array $mehr = []): void {
    http_response_code($status);
    echo json_encode(['ok' => false, 'fehler' => $text] + $mehr, JSON_UNESCAPED_UNICODE);
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

function konfig_datei(string $name = 'db.ini'): string {
    $ordner = __DIR__;
    for ($i = 0; $i < 8; $i++) {
        $kandidat = $ordner . '/waagenspiel-config/' . $name;
        if (is_readable($kandidat)) {
            return $kandidat;
        }
        $ordner = dirname($ordner);
    }
    fehler('Nicht eingerichtet: ' . $name, 500);
}

/** Bricht ab, wenn der Kopf X-Waagenspiel-Verwaltung nicht den Verwaltungsschluessel traegt. */
function verwaltung_pruefen(): void {
    $soll = trim((string) file_get_contents(konfig_datei('verwaltung.txt')));
    $ist = (string) ($_SERVER['HTTP_X_WAAGENSPIEL_VERWALTUNG'] ?? '');
    if (strlen($soll) < 32 || !hash_equals($soll, $ist)) {
        fehler('Kein Zugriff', 403);
    }
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
    $pdo->exec('CREATE TABLE IF NOT EXISTS ' . t('rekord') . " (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        kategorie VARCHAR(20) NOT NULL,
        name VARCHAR(20) NOT NULL,
        punkte INT NOT NULL,
        erreicht DATETIME NOT NULL,
        KEY kategorie_punkte (kategorie, punkte)
    ) $opt");
    raetsel_tabelle_anlegen($pdo, t('raetsel'));
    $pdo->exec('CREATE TABLE IF NOT EXISTS ' . t('statistik') . " (
        raetsel_id INT UNSIGNED NOT NULL,
        modus VARCHAR(5) NOT NULL,
        gespielt INT UNSIGNED NOT NULL DEFAULT 0,
        richtig INT UNSIGNED NOT NULL DEFAULT 0,
        zeit_ms BIGINT UNSIGNED NOT NULL DEFAULT 0,
        PRIMARY KEY (raetsel_id, modus)
    ) $opt");
    $pdo->exec('CREATE TABLE IF NOT EXISTS ' . t('marke') . " (
        kennung CHAR(32) PRIMARY KEY,
        benutzt DATETIME NOT NULL
    ) $opt");
    $pdo->exec('CREATE TABLE IF NOT EXISTS ' . t('einstellung') . " (
        schluessel VARCHAR(40) PRIMARY KEY,
        wert TEXT NOT NULL
    ) $opt");
}

/** Raetsel aus dem Katalog: id = Position in data/katalog.json.gz, nr = laufende Nummer je Stufe. */
function raetsel_tabelle_anlegen(PDO $pdo, string $name): void {
    $pdo->exec("CREATE TABLE IF NOT EXISTS $name (
        id INT UNSIGNED PRIMARY KEY,
        stufe TINYINT UNSIGNED NOT NULL,
        nr INT UNSIGNED NOT NULL,
        abkuerzung TINYINT UNSIGNED NOT NULL,
        waagen VARCHAR(120) NOT NULL,
        UNIQUE KEY stufe_nr (stufe, nr)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
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

// --- Name ----------------------------------------------------------------------------------

function name_pruefen(string $name): string {
    $name = trim(preg_replace('~\s+~u', ' ', $name) ?? '');
    if (!preg_match(NAME_MUSTER, $name)) {
        fehler('Name: 1 bis 20 Zeichen, Buchstaben, Ziffern, Leerzeichen und . _ - ! ?');
    }
    return $name;
}
