// Verbindung zur globalen Bestenliste (bestenliste.php). Keine Oberflaeche.
//
// Je Kategorie ("Mittel/60s") gibt es einen Rekord; eintragen darf sich nur, wer
// ihn bricht. Fuer jede Partie auf Zeit holt das Spiel beim Start eine Marke,
// die der Server erst nach Ablauf der Spielzeit annimmt.

export class GlobalBoard {
  constructor(url = "bestenliste.php", fetchFn = (...args) => fetch(...args)) {
    this.url = url;
    this.fetch = fetchFn;
  }

  async request(body) {
    const options = body
      ? { method: "POST", body: new URLSearchParams(body), headers: { Accept: "application/json" } }
      : { headers: { Accept: "application/json" } };
    const response = await this.fetch(this.url, options);
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error("Die Bestenliste ist gerade nicht erreichbar.");
    }
    if (!data.ok) {
      const error = new Error(data.fehler || "Unbekannter Fehler");
      error.records = data.rekorde;
      throw error;
    }
    return data;
  }

  /** Alle Rekorde: {kategorie: {name, punkte, datum, verlauf: [...]}} */
  async records() {
    return (await this.request()).rekorde || {};
  }

  /** Marke fuer eine Partie, beim Start holen. */
  async start(category) {
    return (await this.request({ aktion: "start", kategorie: category })).marke;
  }

  /** Neuen Rekord eintragen; liefert die neuen Rekorde. */
  async submit(token, category, points, name) {
    const data = await this.request({ aktion: "eintragen", marke: token, kategorie: category, punkte: points, name });
    return data.rekorde;
  }
}

/** Ist `points` ein neuer Rekord gegenueber `record` (oder gibt es noch keinen)? */
export function beatsRecord(points, record) {
  return points > 0 && (!record || points > record.punkte);
}

/** Erlaubte Namen wie auf dem Server: 1-20 Zeichen, Buchstaben, Ziffern, Leerzeichen, . _ - ! ? */
export function validName(name) {
  const trimmed = name.trim().replace(/\s+/gu, " ");
  return /^[\p{L}\p{N} ._\-!?]{1,20}$/u.test(trimmed) ? trimmed : null;
}
