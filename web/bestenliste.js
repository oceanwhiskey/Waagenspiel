// Verbindung zu bestenliste.php. Keine Oberflaeche.
//
// Die Bestenliste ist eine Rekord-Historie je Schwierigkeit und Zeit: Wer den
// Rekord bricht, traegt sich mit einem frei gewaehlten Namen ein. Es gibt keine
// Anmeldung; der zuletzt benutzte Name wird nur im Browser vorgeschlagen.

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

  /** {kategorie: [{name, punkte, datum}, ...]}, hoechster (aktueller) Rekord zuerst. */
  async lists() {
    return (await request(this.fetchFn, this.url)).listen || {};
  }

  /** Marke fuer eine Partie, beim Start holen. */
  async start(category) {
    return (await request(this.fetchFn, this.url, { aktion: "start", kategorie: category })).marke;
  }

  /** Rekord eintragen: liefert die neue Liste der Kategorie. Kein Rekord mehr: Fehler 409. */
  async submit(token, category, points, name) {
    return (await request(this.fetchFn, this.url,
      { aktion: "eintragen", marke: token, kategorie: category, punkte: points, name })).liste;
  }
}

/** Aktueller Rekord einer Kategorie (0, wenn noch keiner steht). */
export function recordOf(lists, category) {
  return lists?.[category]?.[0]?.punkte ?? 0;
}

/** Erlaubte Namen wie auf dem Server: 1-20 Zeichen, Buchstaben, Ziffern, Leerzeichen, . _ - ! ? */
export function validName(name) {
  const trimmed = name.trim().replace(/\s+/gu, " ");
  return /^[\p{L}\p{N} ._\-!?]{1,20}$/u.test(trimmed) ? trimmed : null;
}
