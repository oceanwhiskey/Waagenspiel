// Verbindung zu spieler.php und bestenliste.php. Keine Oberflaeche.
//
// Spielername ohne Passwort und E-Mail (docs/04, Abschnitt 2): Der Server gibt
// beim Nehmen eines Namens einen zufaelligen Geraeteschluessel heraus. Er liegt nur
// hier im Browser (storage) und geht mit jedem Aufruf im Kopf
// X-Waagenspiel-Schluessel mit. Ein Name ist nach einem Tag ohne Benutzung wieder
// frei und kann dann von jedem Geraet genommen werden.

const KEY = "waagenspiel.schluessel";
const NAME = "waagenspiel.spielername";

async function request(fetchFn, url, body, key) {
  const headers = { Accept: "application/json" };
  if (key) headers["X-Waagenspiel-Schluessel"] = key;
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

/** Spielername dieses Geraets. */
export class PlayerAccount {
  constructor({ url = "spieler.php", storage, fetchFn = (...a) => fetch(...a) } = {}) {
    Object.assign(this, { url, storage, fetchFn });
  }

  get key() {
    return this.storage?.getItem(KEY) || null;
  }

  /** Zuletzt bekannter Name (fuer die Anzeige, auch offline). */
  get name() {
    return this.key ? this.storage?.getItem(NAME) || null : null;
  }

  remember(name, key) {
    if (key) this.storage?.setItem(KEY, key);
    this.storage?.setItem(NAME, name);
  }

  forget() {
    this.storage?.setItem(KEY, "");
    this.storage?.setItem(NAME, "");
  }

  async call(aktion, fields = {}) {
    try {
      return await request(this.fetchFn, this.url, { aktion, ...fields }, this.key);
    } catch (error) {
      if (error.status === 401) this.forget(); // Name wurde woanders geloescht oder abgemeldet
      throw error;
    }
  }

  /**
   * Nimmt einen Namen: neu, oder einen, der seit einem Tag nicht benutzt wurde.
   * Ist er vergeben, kommt ein Fehler mit status 409 und data.frei_ab (ISO-Zeit).
   */
  async take(name) {
    const data = await this.call("nehmen", { name });
    this.remember(data.name, data.schluessel);
    return data.name;
  }

  /** {name} */
  async me() {
    const data = await this.call("ich");
    this.remember(data.name);
    return data;
  }

  /** Dieses Geraet abmelden; der Name bleibt mit seinen Ergebnissen bestehen. */
  async logout() {
    await this.call("abmelden");
    this.forget();
  }

  async remove() {
    await this.call("loeschen");
    this.forget();
  }
}

/** Bestenliste: Top 10 je Kategorie, Eintrag nur mit Spielernamen. */
export class GlobalBoard {
  constructor({ url = "bestenliste.php", account, fetchFn = (...a) => fetch(...a) } = {}) {
    Object.assign(this, { url, account, fetchFn });
  }

  /** {kategorie: [{name, punkte, datum}, ...]} */
  async lists() {
    return (await request(this.fetchFn, this.url)).listen || {};
  }

  /** Marke fuer eine Partie, beim Start holen. */
  async start(category) {
    return (await request(this.fetchFn, this.url, { aktion: "start", kategorie: category }, this.account?.key)).marke;
  }

  /** Ergebnis eintragen: {platz, verbessert, bestes, liste}. */
  async submit(token, category, points) {
    try {
      return await request(this.fetchFn, this.url,
        { aktion: "eintragen", marke: token, kategorie: category, punkte: points }, this.account.key);
    } catch (error) {
      if (error.status === 401) this.account.forget();
      throw error;
    }
  }
}

/** Erlaubte Namen wie auf dem Server: 1-20 Zeichen, Buchstaben, Ziffern, Leerzeichen, . _ - ! ? */
export function validName(name) {
  const trimmed = name.trim().replace(/\s+/gu, " ");
  return /^[\p{L}\p{N} ._\-!?]{1,20}$/u.test(trimmed) ? trimmed : null;
}
