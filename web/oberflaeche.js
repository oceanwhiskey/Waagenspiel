// Oberflaeche der Web-Version. Sie zeichnet und nimmt Eingaben an; alles, was das
// Spiel entscheidet, kommt aus einer GameSession (spiel.js), die makeSession liefert.

import {
  DIFFICULTIES,
  GameSession,
  Highscores,
  LEVEL_TITLES,
  RoundSource,
  explain,
  pickCharacters,
  stepsFor,
  streakFactor,
} from "./spiel.js";
import { ScaleDrawing, animateTilt, character, characterIcon } from "./figuren.js";
import { GlobalBoard, beatsRecord, validName } from "./bestenliste.js";

const $ = (id) => document.getElementById(id);
const SPOTS = [[118, 40], [242, 200], [118, 360]]; // oben links, Mitte rechts, unten links
const TIMES = [30, 60, 90, 120, null];

// localStorage kann fehlen oder gesperrt sein (privater Modus): dann ohne Speichern spielen.
const store = {
  getItem(key) {
    try { return localStorage.getItem(key); } catch { return null; }
  },
  setItem(key, value) {
    try { localStorage.setItem(key, value); } catch { /* egal */ }
  },
};

// --- Ton (ganz leise Pieptoene, abschaltbar) ------------------------------------

class Sound {
  constructor(storage) {
    this.storage = storage;
    this.on = storage?.getItem("waagenspiel.ton") !== "aus";
    this.ctx = null;
  }
  toggle() {
    this.on = !this.on;
    try { this.storage?.setItem("waagenspiel.ton", this.on ? "an" : "aus"); } catch { /* egal */ }
  }
  play(notes) {
    if (!this.on) return;
    try {
      this.ctx ??= new (window.AudioContext || window.webkitAudioContext)();
      let t = this.ctx.currentTime;
      for (const [freq, dur] of notes) {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = "triangle";
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.12, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + dur);
        osc.connect(gain).connect(this.ctx.destination);
        osc.start(t);
        osc.stop(t + dur);
        t += dur * 0.8;
      }
    } catch { /* ohne Ton weiterspielen */ }
  }
  right() { this.play([[660, 0.12], [990, 0.18]]); }
  wrong() { this.play([[220, 0.25]]); }
  levelUp() { this.play([[523, 0.1], [659, 0.1], [784, 0.1], [1047, 0.22]]); }
}

// --- Fenster ----------------------------------------------------------------------

class App {
  constructor({ makeSession, highscores, sound, board }) {
    Object.assign(this, { makeSession, highscores, sound, board });
    this.records = null; // globale Rekorde, sobald geladen
    this.boardTime = 60;
    const savedLevel = store.getItem("waagenspiel.stufe");
    this.difficulty = savedLevel in DIFFICULTIES ? savedLevel : "Steigend";
    const savedTime = store.getItem("waagenspiel.zeit");
    const time = savedTime === "ueben" ? null : Number(savedTime);
    this.timeLimit = savedTime !== null && TIMES.includes(time) ? time : 60;
    this.session = null;
    this.round = null;
    this.accepting = false;
    this.timers = new Set();
    this.hintIndex = 0;
    this.preview = pickCharacters(Math.random);
    this.bind();
    this.showStart();
  }

  later(ms, fn) {
    const id = setTimeout(() => { this.timers.delete(id); fn(); }, ms);
    this.timers.add(id);
  }

  clearTimers() {
    this.timers.forEach(clearTimeout);
    this.timers.clear();
    cancelAnimationFrame(this.clockFrame);
  }

  show(id) {
    for (const s of ["start", "spiel", "ende", "bestenliste"]) $(s).hidden = s !== id;
    $("blatt").hidden = true;
  }

  bind() {
    $("los").onclick = () => this.startGame();
    $("nochmal").onclick = () => this.startGame();
    $("menue").onclick = () => this.showStart();
    $("zurueck").onclick = () => this.leave();
    $("tipp").onclick = () => this.showHint();
    $("blatt-mehr").onclick = () => this.showHint();
    $("blatt-ok").onclick = () => this.closeSheet();
    $("blatt-kopf").onclick = () => {
      const closed = $("blatt").classList.toggle("zu");
      $("blatt-kopf").setAttribute("aria-expanded", String(!closed));
    };
    $("ton").onclick = () => { this.sound.toggle(); this.updateSoundLabel(); };
    $("zur-bestenliste").onclick = () => this.showBoard();
    $("liste-zurueck").onclick = () => this.showStart();
    $("welt-form").onsubmit = (e) => { e.preventDefault(); this.submitRecord(); };
    document.addEventListener("keydown", (e) => this.onKey(e));
  }

  onKey(e) {
    if (e.target instanceof HTMLInputElement) return; // Namensfeld: Tasten gehoeren dem Feld
    const key = e.key.toLowerCase();
    if (key === "escape") return $("bestenliste").hidden ? this.leave() : this.showStart();
    if (!$("start").hidden && key === "enter") return this.startGame();
    if (!$("ende").hidden && key === "enter") return this.startGame();
    if (["1", "2", "3", "4"].includes(key) && this.accepting) return this.choose(Number(key) - 1);
    if (key === "h" && this.session?.isPractice && this.accepting) return this.showHint();
    if ((key === "enter" || key === " ") && !$("blatt").hidden) {
      e.preventDefault();
      this.closeSheet();
    }
  }

  // --- Start ------------------------------------------------------------------------

  showStart() {
    this.clearTimers();
    this.session = null;
    this.show("start");
    this.chips("wahl-stufe", Object.keys(DIFFICULTIES), (d) => d, this.difficulty, (d) => {
      this.difficulty = d;
      store.setItem("waagenspiel.stufe", d);
    });
    this.chips("wahl-zeit", TIMES, (t) => (t ? `${t} s` : "Üben"), this.timeLimit, (t) => {
      this.timeLimit = t;
      store.setItem("waagenspiel.zeit", t ?? "ueben");
    });
    this.updateRecord();
    this.updateSoundLabel();
    this.drawLogo();
    this.loadRecords().then(() => this.updateRecord());
  }

  chips(id, values, label, selected, onSelect) {
    const box = $(id);
    box.replaceChildren();
    for (const value of values) {
      const chip = document.createElement("button");
      chip.className = "chip";
      chip.setAttribute("role", "radio");
      chip.setAttribute("aria-checked", String(value === selected));
      chip.textContent = label(value);
      chip.onclick = () => {
        onSelect(value);
        box.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-checked", String(c === chip)));
        this.updateRecord();
      };
      box.appendChild(chip);
    }
  }

  updateRecord() {
    const best = this.highscores.get(Highscores.key(this.difficulty, this.timeLimit));
    $("rekord").textContent = this.timeLimit == null
      ? "Üben: ohne Uhr, mit Tipps und Erklärungen"
      : best ? `Dein Rekord: ${best} Punkte` : "Noch kein eigener Rekord – stell den ersten auf!";
    const world = this.timeLimit == null ? null : this.records?.[Highscores.key(this.difficulty, this.timeLimit)];
    $("weltrekord").textContent = this.timeLimit == null || !this.records ? ""
      : world ? `Bestenliste: ${world.name} mit ${world.punkte} Punkten` : "Bestenliste: noch frei – sei die oder der Erste!";
  }

  // --- Globale Bestenliste ------------------------------------------------------------

  async loadRecords() {
    try {
      this.records = await this.board.records();
    } catch {
      this.records = null; // ohne Netz geht es eben ohne Bestenliste
    }
    return this.records;
  }

  showBoard() {
    this.clearTimers();
    this.session = null;
    this.show("bestenliste");
    this.chips("liste-zeit", TIMES.filter(Boolean), (t) => `${t} s`, this.boardTime, (t) => {
      this.boardTime = t;
      this.renderBoard();
    });
    $("liste-status").textContent = "wird geladen …";
    this.renderBoard();
    this.loadRecords().then(() => this.renderBoard());
  }

  renderBoard() {
    const table = $("liste");
    $("liste-status").textContent = this.records ? "" : "Die Bestenliste ist gerade nicht erreichbar.";
    table.replaceChildren(...Object.keys(DIFFICULTIES).map((difficulty) => {
      const row = document.createElement("tr");
      const name = document.createElement("td");
      name.textContent = difficulty;
      const cell = document.createElement("td");
      const record = this.records?.[Highscores.key(difficulty, this.boardTime)];
      if (record) {
        const who = document.createElement("span");
        who.className = "who";
        who.textContent = record.name;
        const when = document.createElement("span");
        when.className = "when";
        when.textContent = new Date(record.datum).toLocaleDateString("de-DE");
        cell.append(`${record.punkte}`, who, when);
      } else {
        const empty = document.createElement("span");
        empty.className = "empty";
        empty.textContent = this.records ? "noch frei" : "–";
        cell.append(empty);
      }
      row.append(name, cell);
      return row;
    }));
  }

  async offerRecord(key, points, token) {
    const box = $("welt");
    $("welt-form").hidden = true;
    $("welt-fehler").textContent = "";
    if (!points || !token) return;
    const records = await this.loadRecords();
    if (!records || $("ende").hidden) return;
    const record = records[key];
    box.hidden = false;
    if (beatsRecord(points, record)) {
      $("welt-text").textContent = record
        ? `Neuer Rekord in der Bestenliste! Bisher: ${record.name} mit ${record.punkte}.`
        : "Du bist die oder der Erste in dieser Kategorie!";
      $("welt-form").hidden = false;
      this.pending = { key, points, token };
      $("welt-name").value = store.getItem("waagenspiel.name") || "";
      $("welt-name").focus();
    } else {
      $("welt-text").textContent = `Rekord in der Bestenliste: ${record.name} mit ${record.punkte} Punkten.`;
    }
  }

  async submitRecord() {
    const pending = this.pending;
    if (!pending) return;
    const name = validName($("welt-name").value);
    if (!name) {
      $("welt-fehler").textContent = "Bitte 1 bis 20 Zeichen: Buchstaben, Ziffern, Leerzeichen, . _ - ! ?";
      return;
    }
    $("welt-senden").disabled = true;
    try {
      this.records = await this.board.submit(pending.token, pending.key, pending.points, name);
      store.setItem("waagenspiel.name", name);
      this.pending = null;
      $("welt-form").hidden = true;
      $("welt-text").textContent = `Eingetragen: ${name} mit ${pending.points} Punkten. Glückwunsch!`;
      this.confetti();
    } catch (error) {
      $("welt-fehler").textContent = error.message;
      if (error.records) this.records = error.records;
    } finally {
      $("welt-senden").disabled = false;
    }
  }

  updateSoundLabel() {
    $("ton").textContent = this.sound.on ? "Ton: an" : "Ton: aus";
  }

  drawLogo() {
    const svg = $("logo");
    svg.replaceChildren();
    const drawing = new ScaleDrawing(svg, 180, 30, { number: 0, left: [0, 1], right: [2, 3, 0], tilt: 0 },
      this.preview, { showNumber: false });
    this.preview.forEach((ch, i) => {
      const fig = character(ch, 22);
      const [x, y] = [[36, 140], [92, 146], [268, 146], [324, 140]][i];
      fig.setAttribute("transform", `translate(${x},${y})`);
      svg.appendChild(fig);
    });
    const start = performance.now();
    const rock = (now) => {
      if ($("start").hidden) return;
      drawing.set(0.12 * Math.sin((now - start) / 500));
      requestAnimationFrame(rock);
    };
    requestAnimationFrame(rock);
  }

  // --- Spiel --------------------------------------------------------------------------

  startGame() {
    this.clearTimers();
    this.preview = pickCharacters(Math.random);
    this.session = this.makeSession(this.difficulty, this.timeLimit, this.preview);
    this.show("spiel");
    const practice = this.session.isPractice;
    $("tipp").hidden = !practice;
    $("uhr").hidden = practice;
    $("zeitbalken").hidden = practice;
    this.drawCards();
    this.token = null;
    if (!practice) {
      const key = Highscores.key(this.difficulty, this.timeLimit);
      this.board.start(key).then((token) => (this.token = token)).catch(() => {});
    }
    this.session.start();
    this.showRound();
    if (!practice) this.tick();
  }

  leave() {
    if (this.session && this.session.rounds) this.showEnd();
    else this.showStart();
  }

  updateHeader() {
    const s = this.session;
    $("stand").textContent = `Runde ${s.rounds + 1}  ✔ ${s.correct}  ✘ ${s.wrong}`;
    $("punkte").textContent = s.isPractice ? "" : `★ ${s.points}`;
    const streak = s.streak >= 2 ? ` · Serie ${s.streak}` : "";
    $("stufe").textContent = `Stufe: ${LEVEL_TITLES[s.difficulty.level]}${streak}`;
  }

  tick() {
    const s = this.session;
    if (!s || s.isPractice) return;
    const left = s.timeLeft();
    const share = left / s.timeLimit;
    $("uhr").textContent = `⏱ ${Math.ceil(left)} s`;
    if (this.accepting) this.showPenalty();
    $("uhr").classList.toggle("knapp", left <= 10);
    const bar = $("zeitbalken").firstElementChild;
    bar.style.width = `${share * 100}%`;
    bar.style.background = left <= 10 ? "var(--bad)" : share < 0.4 ? "var(--gold)" : "var(--good)";
    if (s.isOver()) {
      this.accepting = false;
      this.later(200, () => this.showEnd());
      return;
    }
    this.clockFrame = requestAnimationFrame(() => this.tick());
  }

  drawCards() {
    const box = $("karten");
    box.replaceChildren();
    this.cards = this.session.characters.map((ch, i) => {
      const card = document.createElement("button");
      card.className = "card";
      card.setAttribute("aria-label", ch.name);
      card.append(characterIcon(ch));
      const name = document.createElement("span");
      name.textContent = ch.name;
      const key = document.createElement("span");
      key.className = "key";
      key.textContent = i + 1;
      card.append(name, key);
      card.onclick = () => this.choose(i);
      box.appendChild(card);
      return card;
    });
  }

  resetCards() {
    this.cards.forEach((card) => (card.className = "card"));
  }

  showRound() {
    const s = this.session;
    this.round = s.current;
    this.updateHeader();
    this.resetCards();
    $("blatt").hidden = true;
    $("karten").hidden = false;
    const msg = $("nachricht");
    msg.className = "message";
    msg.textContent = "Welche Figur ist am schwersten?";
    const field = $("feld");
    field.replaceChildren();
    this.drawings = this.round.views.map((view, k) => new ScaleDrawing(field, ...SPOTS[k], view, s.characters));
    this.hintIndex = 0;
    this.accepting = true;
    this.showPenalty();
    animateTilt(this.drawings);
  }

  /** Zeigt, was ein Fehler gerade kosten wuerde (sinkt mit der Bedenkzeit). */
  showPenalty() {
    const s = this.session;
    const box = $("abzug");
    if (!s || s.isPractice || !this.accepting) {
      box.textContent = "";
      return;
    }
    box.innerHTML = `Ein Fehler kostet gerade <b>−${s.currentPenalty()}</b>`;
  }

  choose(choice) {
    if (!this.accepting || !this.session) return;
    this.accepting = false;
    $("abzug").textContent = "";
    const feedback = this.session.answer(choice);
    this.updateHeader();
    if (feedback.correct) this.celebrate(choice, feedback);
    else this.reveal(choice, feedback);
  }

  celebrate(choice, feedback) {
    this.resetCards();
    this.cards[choice].classList.add("richtig");
    this.drawings.forEach((d) => d.mark(choice, "richtig"));
    let text = feedback.points ? `Richtig!  +${feedback.points}` : "Richtig!";
    if (feedback.levelAfter > feedback.levelBefore) {
      text += `  Neue Stufe: ${LEVEL_TITLES[feedback.levelAfter]}!`;
      this.sound.levelUp();
    } else {
      if (feedback.streak >= 2 && feedback.points) {
        text += `  · ${feedback.streak} in Folge ×${String(streakFactor(feedback.streak)).replace(".", ",")}`;
      }
      this.sound.right();
    }
    const msg = $("nachricht");
    msg.className = "message good-text";
    msg.textContent = text;
    if (feedback.points) this.floatPoints(this.cards[choice], `+${feedback.points}`);
    this.later(750, () => this.nextRound());
  }

  floatPoints(card, text, minus = false) {
    const rect = card.getBoundingClientRect();
    const node = document.createElement("div");
    node.className = minus ? "float minus" : "float";
    node.textContent = text;
    node.style.left = `${rect.left + rect.width / 2}px`;
    node.style.top = `${rect.top - 34}px`;
    document.body.appendChild(node);
    setTimeout(() => node.remove(), 800);
  }

  reveal(choice, feedback) {
    const s = this.session;
    this.resetCards();
    this.cards[choice].classList.add("falsch");
    this.cards[feedback.answer].classList.add("loesung");
    this.drawings.forEach((d) => d.mark(feedback.answer, "loesung"));
    this.sound.wrong();
    navigator.vibrate?.(60);
    const right = s.characters[feedback.answer].name;
    const wrong = s.characters[choice].name;
    const msg = $("nachricht");
    msg.className = "message bad-text";
    msg.textContent = `Leider nicht – ${right} ist am schwersten.` + (feedback.points ? `  ${feedback.points}`.replace("-", "−") : "");
    if (feedback.points) this.floatPoints(this.cards[choice], `${feedback.points}`.replace("-", "−"), true);
    if (s.isPractice) {
      const lines = stepsFor(this.round, choice).flatMap((step) => step.text);
      $("karten").hidden = true; // Antwort steht fest: Platz fuer Erklaerung und Waagen
      this.openSheet(`Warum ist ${wrong} leichter als ${right}?`, lines, { more: false, ok: "Weiter" });
      this.afterSheet = () => this.nextRound();
    } else {
      this.later(1000, () => this.nextRound());
    }
  }

  showHint() {
    if (!this.accepting || !this.session?.isPractice) return;
    const hints = this.round.hints;
    if (!hints.length) return;
    const index = Math.min(this.hintIndex, hints.length - 1);
    this.hintIndex = index + 1;
    this.openSheet(`Tipp ${index + 1} von ${hints.length}`, hints[index], {
      more: this.hintIndex < hints.length,
      ok: "OK",
    });
    this.afterSheet = null;
  }

  openSheet(title, lines, { more, ok }) {
    const s = this.session;
    $("blatt-titel").textContent = title;
    const list = $("blatt-text");
    list.replaceChildren(...lines.map((line) => {
      const li = document.createElement("li");
      li.textContent = explain(line, this.round, s.characters);
      return li;
    }));
    $("blatt-mehr").hidden = !more;
    $("blatt-ok").textContent = ok;
    $("blatt").classList.remove("zu");
    $("blatt-kopf").setAttribute("aria-expanded", "true");
    $("blatt").hidden = false;
    list.scrollTop = 0;
  }

  closeSheet() {
    $("blatt").hidden = true;
    const next = this.afterSheet;
    this.afterSheet = null;
    next?.();
  }

  nextRound() {
    const s = this.session;
    if (!s) return;
    if (s.isOver()) return this.showEnd();
    s.nextRound();
    this.showRound();
  }

  // --- Ende ---------------------------------------------------------------------------

  showEnd() {
    const s = this.session;
    if (!s) return;
    this.clearTimers();
    const result = s.result();
    const key = Highscores.key(this.difficulty, this.timeLimit);
    const oldBest = this.highscores.get(key);
    const record = !s.isPractice && this.highscores.submit(key, result.points);
    this.session = null;
    this.accepting = false;
    this.show("ende");
    $("ende-titel").textContent = s.isPractice ? "Gut geübt!" : s.isOver() ? "Zeit ist um!" : "Spiel beendet";
    $("ende-rekord").textContent = record ? "★ Neuer eigener Rekord! ★" : oldBest ? `Dein Rekord: ${oldBest} Punkte` : "";
    $("e-runden").textContent = result.rounds;
    $("e-richtig").textContent = result.correct;
    $("e-falsch").textContent = result.wrong;
    $("e-serie").textContent = result.bestStreak;
    $("e-punkte").textContent = result.points;
    $("ende-figuren").replaceChildren(...this.preview.map((ch) => characterIcon(ch)));
    if (record) this.confetti();
    $("welt").hidden = true;
    this.pending = null;
    // Nur volle Partien auf Zeit kommen in die Bestenliste
    if (!s.isPractice && s.isOver()) this.offerRecord(key, result.points, this.token);
  }

  confetti() {
    const colors = ["#ef476f", "#ffd23f", "#06d6a0", "#3a86ff", "#9b5de5", "#ff8c42"];
    for (let i = 0; i < 70; i++) {
      const piece = document.createElement("div");
      piece.className = "konfetti";
      piece.style.left = `${Math.random() * 100}vw`;
      piece.style.background = colors[i % colors.length];
      piece.style.setProperty("--dx", `${(Math.random() - 0.5) * 120}px`);
      piece.style.animationDuration = `${1.8 + Math.random() * 1.6}s`;
      piece.style.animationDelay = `${Math.random() * 0.6}s`;
      document.body.appendChild(piece);
      setTimeout(() => piece.remove(), 4200);
    }
  }
}

// --- Start ------------------------------------------------------------------------

// Muss zu <meta name="waagenspiel-version"> in index.html passen; bei jedem Update
// beider Dateien erhoehen. Passt es nicht (alte Seite aus dem Browser-Cache, neues
// Skript), wird die Seite einmal neu geladen.
const VERSION = "5";

function pageIsCurrent() {
  const meta = document.querySelector('meta[name="waagenspiel-version"]');
  if (meta?.content === VERSION) return true;
  // Bis zu zweimal neu laden: Beim ersten Mal kann noch der alte Service Worker
  // die alte Seite liefern, beim zweiten Mal ist der neue aktiv.
  let tries = 0;
  try { tries = Number(sessionStorage.getItem(`waagenspiel.neuladen.${VERSION}`)) || 0; } catch { /* egal */ }
  if (tries < 2) {
    try { sessionStorage.setItem(`waagenspiel.neuladen.${VERSION}`, String(tries + 1)); } catch { /* egal */ }
    setTimeout(() => location.reload(), tries * 400);
    return false;
  }
  return true; // lieber mit Fehlerhinweis weiter als endlos laden
}

async function main() {
  if (!pageIsCurrent()) return;
  const button = $("los");
  button.disabled = true;
  $("laden").textContent = "Rätsel werden geladen …";
  let data;
  try {
    data = await (await fetch("raetsel.json")).json();
  } catch {
    $("laden").textContent = "Die Rätsel konnten nicht geladen werden. Bitte Seite neu laden.";
    return;
  }
  const source = new RoundSource(data.levels);
  let app;
  try {
    app = new App({
      makeSession: (difficulty, timeLimit, characters) =>
        new GameSession({ source, difficulty: DIFFICULTIES[difficulty](), timeLimit, characters }),
      highscores: new Highscores(store),
      sound: new Sound(store),
      board: new GlobalBoard(),
    });
  } catch (error) {
    $("laden").textContent = "Das Spiel wurde gerade aktualisiert. Bitte die Seite neu laden.";
    throw error;
  }
  window.waagenspiel = app; // fuer Tests im Browser
  button.disabled = false;
  $("laden").textContent = "";
  if ("serviceWorker" in navigator && location.protocol === "https:") {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
}

main();
