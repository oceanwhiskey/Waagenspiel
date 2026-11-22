// Verbindung zum Server (bestenliste.php, raetsel.php). Keine Oberflaeche.
//
// Nach jeder vollen Partie auf Zeit darf man sich mit einem frei gewaehlten Namen
// in die Bestenliste eintragen. Es gibt keine Anmeldung; der zuletzt benutzte
// Name wird nur im Browser vorgeschlagen.

async function request(fetchFn, url, body) {
  const headers = { Accept: "application/json" };
  const options = body ? { method: "POST", body: new URLSearchParams(body), headers } : { headers };
  let response;
  let data;
  try {
    response = await fetchFn(url, options);
    data = await response.json();
  } catch {
    throw new Error("Der Server ist gerade nicht erreichbar.");
  }
  if (!data.ok) {
    const error = new Error(data.fehler || "Unbekannter Fehler");
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

export class GlobalBoard {
  constructor({ url = "bestenliste.php", fetchFn = (...a) => fetch(...a) } = {}) {
    Object.assign(this, { url, fetchFn });
  }

  /** {kategorie: [{name, punkte, datum}, ...]}, bester zuerst. */
  async lists() {
    return (await request(this.fetchFn, this.url)).listen || {};
  }

  /** Marke fuer eine Partie, beim Start holen. */
  async start(category) {
    return (await request(this.fetchFn, this.url, { aktion: "start", kategorie: category })).marke;
  }

  /** Ergebnis eintragen: {platz, liste} (neue Liste der Kategorie). */
  async submit(token, category, points, name) {
    const data = await request(this.fetchFn, this.url,
      { aktion: "eintragen", marke: token, kategorie: category, punkte: points, name });
    return { platz: data.platz, liste: data.liste };
  }
}

/** Raetsel vom Server und anonyme Zaehler je Raetsel (gespielt, richtig, Bedenkzeit). */
export class PuzzleServer {
  constructor({ url = "raetsel.php", fetchFn = (...a) => fetch(...a), beacon = navigator.sendBeacon?.bind(navigator) } = {}) {
    Object.assign(this, { url, fetchFn, beacon });
  }

  /** Zufaellige Raetsel einer Stufe: [{id, s: [...]}, ...]; leer, wenn der Server keine hat. */
  async batch(level, count) {
    return (await request(this.fetchFn, `${this.url}?stufe=${level}&anzahl=${count}`)).raetsel || [];
  }

  /** Meldet eine Antwort; ohne Netz geht sie verloren, das ist egal. */
  report(id, mode, correct, ms) {
    if (id == null) return;
    const body = new URLSearchParams({ aktion: "antwort", id, modus: mode, richtig: correct ? 1 : 0, ms: Math.max(0, ms) });
    try {
      if (this.beacon?.(this.url, body)) return;
      this.fetchFn(this.url, { method: "POST", body, keepalive: true }).catch(() => {});
    } catch {
      /* egal */
    }
  }
}

/** Aktueller Rekord einer Kategorie (0, wenn noch keiner steht). */
export function recordOf(lists, category) {
  return lists?.[category]?.[0]?.punkte ?? 0;
}

/** Platz, den `points` in der Liste haetten (bei Gleichstand hinter den frueheren). */
export function rankFor(list, points) {
  return (list || []).filter((entry) => entry.punkte >= points).length + 1;
}

/** Erlaubte Namen wie auf dem Server: 1-20 Zeichen, Buchstaben, Ziffern, Leerzeichen, . _ - ! ? */
export function validName(name) {
  const trimmed = name.trim().replace(/\s+/gu, " ");
  return /^[\p{L}\p{N} ._\-!?]{1,20}$/u.test(trimmed) ? trimmed : null;
}
