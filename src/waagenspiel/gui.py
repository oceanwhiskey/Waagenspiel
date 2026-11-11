"""Grafische Oberflaeche des Waagenspiels (tkinter).

Die Oberflaeche zeichnet nur und nimmt Eingaben an. Alles, was das Spiel
entscheidet, kommt aus einer :class:`waagenspiel.game.GameSession`, die
``make_session`` liefert (Dependency Injection).

Bedienung: Figur anklicken oder 1-4 druecken. Im Uebungsmodus gibt H einen
Tipp, Enter geht weiter. Esc fuehrt zurueck ins Menue.
"""

from __future__ import annotations

import math
import random
import tkinter as tk
from typing import Callable, Sequence

from .game import (
    DIFFICULTIES,
    LEVEL_TITLES,
    Character,
    Feedback,
    GameSession,
    Highscores,
    Round,
    ScaleView,
    explain_with_names,
    pan_positions,
    pick_characters,
)

SessionFactory = Callable[[str, "float | None", Sequence[Character]], GameSession]

WIDTH, HEIGHT = 1000, 720
FONT = "Segoe UI"
TITLE_FONT = ("Segoe UI Black", 46)
INK = "#2b2d42"
SOFT_INK = "#6c757d"
BRASS = "#e0a526"
BRASS_DARK = "#9c6b00"
GOOD = "#2a9d8f"
BAD = "#e63946"
GOLD = "#ffb703"
PANEL = "#ffffff"

# Lage der Waagen: oben links, Mitte rechts, unten links (Drehpunkt).
SCALE_SPOTS = ((255, 112), (745, 257), (255, 402))
SIDEBAR = 300  # Breite der Tipp-Leiste im Uebungsmodus
TIME_CHOICES: tuple[float | None, ...] = (30, 60, 90, 120, None)


# --------------------------------------------------------------------------
# Zeichenhelfer
# --------------------------------------------------------------------------


def shade(color: str, factor: float) -> str:
    """Hellt auf (factor > 0, Richtung Weiss) oder dunkelt ab (factor < 0)."""

    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    if factor >= 0:
        r, g, b = (round(v + (255 - v) * factor) for v in (r, g, b))
    else:
        r, g, b = (round(v * (1 + factor)) for v in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def rounded_rect(canvas: tk.Canvas, x0: float, y0: float, x1: float, y1: float, radius: float, **options) -> int:
    r = radius
    points = [
        x0 + r, y0, x0 + r, y0, x1 - r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y0 + r,
        x1, y1 - r, x1, y1 - r, x1, y1, x1 - r, y1, x1 - r, y1, x0 + r, y1, x0 + r, y1,
        x0, y1, x0, y1 - r, x0, y1 - r, x0, y0 + r, x0, y0 + r, x0, y0,
    ]
    return canvas.create_polygon(points, smooth=True, **options)


def draw_character(
    canvas: tk.Canvas, x: float, y: float, r: float, character: Character, tags: Sequence[str] = (), mood: str = "calm"
) -> None:
    """Zeichnet eine Figur: Form in ihrer Farbe mit Gesicht."""

    tags = tuple(tags)
    fill, line = character.color, shade(character.color, -0.4)
    width = max(2, round(r / 10))
    face_y = y
    if character.shape == "kreis":
        canvas.create_oval(x - r, y - r, x + r, y + r, fill=fill, outline=line, width=width, tags=tags)
    elif character.shape == "quadrat":
        rounded_rect(canvas, x - 0.92 * r, y - 0.92 * r, x + 0.92 * r, y + 0.92 * r, 0.45 * r,
                     fill=fill, outline=line, width=width, tags=tags)
    elif character.shape == "dreieck":
        top, left, right = (x, y - 1.15 * r), (x - 1.1 * r, y + 0.9 * r), (x + 1.1 * r, y + 0.9 * r)
        points = [*top, *top, *right, *right, *left, *left]
        canvas.create_polygon(points, smooth=True, fill=fill, outline=line, width=width, tags=tags)
        face_y = y + 0.28 * r
    else:  # tropfen
        points = [x, y - 1.25 * r, x + 0.35 * r, y - 0.75 * r, x + r, y - 0.05 * r, x + r, y + 0.45 * r,
                  x + 0.6 * r, y + r, x, y + r, x - 0.6 * r, y + r, x - r, y + 0.45 * r, x - r, y - 0.05 * r,
                  x - 0.35 * r, y - 0.75 * r]
        canvas.create_polygon(points, smooth=True, fill=fill, outline=line, width=width, tags=tags)
        face_y = y + 0.2 * r
    # Augen
    eye_r, pupil_r = 0.24 * r, 0.12 * r
    for dx in (-0.36 * r, 0.36 * r):
        ex, ey = x + dx, face_y - 0.15 * r
        canvas.create_oval(ex - eye_r, ey - eye_r, ex + eye_r, ey + eye_r, fill="white", outline=line,
                           width=1, tags=tags)
        py = ey + (0.05 * r if mood != "wow" else -0.04 * r)
        canvas.create_oval(ex - pupil_r, py - pupil_r, ex + pupil_r, py + pupil_r, fill=INK, outline="", tags=tags)
        canvas.create_oval(ex - 0.04 * r, py - 0.07 * r, ex + 0.03 * r, py, fill="white", outline="", tags=tags)
    # Baeckchen
    for dx in (-0.62 * r, 0.62 * r):
        cy = face_y + 0.18 * r
        canvas.create_oval(x + dx - 0.13 * r, cy - 0.08 * r, x + dx + 0.13 * r, cy + 0.08 * r,
                           fill=shade(fill, -0.15), outline="", tags=tags)
    # Mund
    my = face_y + 0.22 * r
    if mood == "wow":
        canvas.create_oval(x - 0.1 * r, my - 0.04 * r, x + 0.1 * r, my + 0.2 * r, fill=INK, outline="", tags=tags)
    elif mood == "happy":
        canvas.create_arc(x - 0.3 * r, my - 0.22 * r, x + 0.3 * r, my + 0.28 * r, start=180, extent=180,
                          fill=INK, outline=INK, style=tk.CHORD, tags=tags)
    else:
        canvas.create_arc(x - 0.22 * r, my - 0.16 * r, x + 0.22 * r, my + 0.16 * r, start=200, extent=140,
                          style=tk.ARC, outline=INK, width=max(1, round(r / 12)), tags=tags)


class ScaleDrawing:
    """Eine Balkenwaage mit Schalen und Figuren; der Balken laesst sich neigen."""

    ARM = 100  # halbe Balkenlaenge
    DROP = 92  # vom Balkenende bis zur Schale
    PAN = 50  # halbe Schalenbreite
    ITEM = 21  # Radius einer Figur auf der Waage
    MAX_ANGLE = math.radians(11)

    def __init__(self, canvas: tk.Canvas, x: float, y: float, view: ScaleView, characters: Sequence[Character],
                 tag: str, show_number: bool = True) -> None:
        self.canvas, self.x, self.y, self.view, self.tag = canvas, x, y, view, tag
        self.characters = characters
        self.angle = 0.0
        c = canvas
        # Standfuss und Saeule
        c.create_polygon(x - 52, y + 132, x + 52, y + 132, x + 30, y + 116, x - 30, y + 116, smooth=False,
                         fill=BRASS, outline=BRASS_DARK, width=2, tags=(tag,))
        c.create_rectangle(x - 6, y, x + 6, y + 117, fill=BRASS, outline=BRASS_DARK, width=2, tags=(tag,))
        if show_number:
            c.create_oval(x - 14, y + 64, x + 14, y + 92, fill="white", outline=BRASS_DARK, width=2, tags=(tag,))
            c.create_text(x, y + 78, text=str(view.number), font=(FONT, 12, "bold"), fill=INK, tags=(tag,))
        # Balken, Schnuere, Schalen
        (lx, ly), (rx, ry) = self._ends(0.0)
        self.beam = c.create_line(lx, ly, rx, ry, width=8, fill=BRASS, capstyle=tk.ROUND, tags=(tag,))
        self.strings: list[tuple[int, int, int]] = []
        self.pans: list[str] = []
        self.items: list[tuple[str, int, float, float]] = []
        for side, (ex, ey), contents in ((0, (lx, ly), view.left), (1, (rx, ry), view.right)):
            a = c.create_line(ex, ey, ex - self.PAN + 6, ey + self.DROP, fill=BRASS_DARK, width=2, tags=(tag,))
            b = c.create_line(ex, ey, ex + self.PAN - 6, ey + self.DROP, fill=BRASS_DARK, width=2, tags=(tag,))
            self.strings.append((side, a, b))
            pan_tag = f"{tag}_pan{side}"
            self.pans.append(pan_tag)
            self._draw_pan(ex, ey + self.DROP, contents, pan_tag)
        c.create_oval(x - 9, y - 9, x + 9, y + 9, fill=BRASS, outline=BRASS_DARK, width=2, tags=(tag,))
        self.pan_origin = [self._ends(0.0)[0], self._ends(0.0)[1]]

    def _ends(self, angle: float) -> tuple[tuple[float, float], tuple[float, float]]:
        dx, dy = self.ARM * math.cos(angle), self.ARM * math.sin(angle)
        return (self.x - dx, self.y - dy), (self.x + dx, self.y + dy)

    def _draw_pan(self, px: float, py: float, contents: Sequence[int], pan_tag: str) -> None:
        c, r = self.canvas, self.ITEM
        tags = (self.tag, pan_tag)
        for (offset, row), who in zip(pan_positions(len(contents)), contents):
            ix = px + offset * 2.05 * r
            iy = py - r - 2 - row * 1.72 * r
            draw_character(c, ix, iy, r, self.characters[who], tags)
            self.items.append((pan_tag, who, ix, iy))
        c.create_polygon(px - self.PAN, py, px + self.PAN, py, px + self.PAN - 10, py + 13, px - self.PAN + 10,
                         py + 13, smooth=False, fill=BRASS, outline=BRASS_DARK, width=2, tags=tags)

    def set_angle(self, angle: float) -> None:
        c = self.canvas
        old = self._ends(self.angle)
        new = self._ends(angle)
        self.angle = angle
        c.coords(self.beam, *new[0], *new[1])
        for side, a, b in self.strings:
            ex, ey = new[side]
            c.coords(a, ex, ey, ex - self.PAN + 6, ey + self.DROP)
            c.coords(b, ex, ey, ex + self.PAN - 6, ey + self.DROP)
            c.move(self.pans[side], new[side][0] - old[side][0], new[side][1] - old[side][1])

    @property
    def target_angle(self) -> float:
        return self.view.tilt * self.MAX_ANGLE

    def mark(self, who: int, color: str) -> None:
        """Legt einen Ring um jede Figur ``who`` auf dieser Waage."""

        ends = self._ends(self.angle)
        for pan_tag, item_who, ix, iy in self.items:
            if item_who != who:
                continue
            side = self.pans.index(pan_tag)
            dx = ends[side][0] - self.pan_origin[side][0]
            dy = ends[side][1] - self.pan_origin[side][1]
            r = self.ITEM + 6
            self.canvas.create_oval(ix + dx - r, iy + dy - r, ix + dx + r, iy + dy + r, outline=color, width=4,
                                    tags=(self.tag, pan_tag, "marks"))


# --------------------------------------------------------------------------
# Fenster
# --------------------------------------------------------------------------


class GameWindow:
    """Startbildschirm, Spiel und Auswertung auf einer einzigen Zeichenflaeche."""

    def __init__(
        self,
        root: tk.Tk,
        make_session: SessionFactory,
        highscores: Highscores,
        time_limit: float | None = 60,
        difficulty: str = "Steigend",
    ) -> None:
        self.root = root
        self.make_session = make_session
        self.highscores = highscores
        self.time_limit = time_limit
        self.difficulty = difficulty
        self.time_choices = TIME_CHOICES if time_limit in TIME_CHOICES else (time_limit, *TIME_CHOICES)
        self.generation = 0
        self.session: GameSession | None = None
        self.round: Round | None = None
        self.drawings: list[ScaleDrawing] = []
        self.accepting = False
        self.waiting_for_next = False
        self.hint_index = 0
        self.preview = pick_characters(random.Random())

        root.title("Waagen-Spiel")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, highlightthickness=0, bg="#eaf6ff")
        self.canvas.pack()
        root.bind("<Key>", self._on_key)
        self.show_start_screen()

    # --- Grundgeruest ---------------------------------------------------------

    def _new_screen(self, width: int = WIDTH) -> None:
        """Leert die Zeichenflaeche; ``width`` > WIDTH laesst Platz fuer die Tipp-Leiste."""

        self.generation += 1
        self.accepting = False
        self.waiting_for_next = False
        c = self.canvas
        c.delete("all")
        c.configure(width=width)
        top, bottom = (0xEA, 0xF6, 0xFF), (0xFF, 0xF3, 0xDF)
        steps = 48
        for i in range(steps):
            t = i / (steps - 1)
            color = "#%02x%02x%02x" % tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
            y0 = HEIGHT * i / steps
            c.create_rectangle(0, y0, width, y0 + HEIGHT / steps + 1, fill=color, outline="")

    def later(self, ms: int, action: Callable[[], None]) -> None:
        """Wie ``after``, verfaellt aber beim Wechsel des Bildschirms."""

        generation = self.generation

        def run() -> None:
            if generation == self.generation:
                action()

        self.root.after(ms, run)

    def button(self, x: float, y: float, w: float, h: float, text: str, command: Callable[[], None],
               color: str = GOOD, size: int = 16, selected: bool | None = None) -> str:
        c = self.canvas
        tag = f"button{id(command)}_{x}_{y}"
        fill = color if selected in (None, True) else "#ffffff"
        ink = "white" if selected in (None, True) else INK
        outline = shade(color, -0.25)
        rounded_rect(c, x - w / 2 + 3, y - h / 2 + 5, x + w / 2 + 3, y + h / 2 + 5, 16, fill=shade(color, -0.35)
                     if selected in (None, True) else "#d9dee3", outline="", tags=(tag,))
        body = rounded_rect(c, x - w / 2, y - h / 2, x + w / 2, y + h / 2, 16, fill=fill, outline=outline, width=2,
                            tags=(tag,))
        c.create_text(x, y, text=text, font=(FONT, size, "bold"), fill=ink, tags=(tag,))
        c.tag_bind(tag, "<Button-1>", lambda _e: command())
        c.tag_bind(tag, "<Enter>", lambda _e: (c.itemconfigure(body, fill=shade(fill, 0.15) if selected in (None, True)
                                                               else shade(color, 0.75)), c.config(cursor="hand2")))
        c.tag_bind(tag, "<Leave>", lambda _e: (c.itemconfigure(body, fill=fill), c.config(cursor="")))
        return tag

    def _on_key(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if key == "escape":
            if self.session is not None and self.session.rounds:
                self.show_end_screen()
            else:
                self.show_start_screen()
        elif self.session is None:
            if key in ("return", "space"):
                self.start_game()
        elif key in ("1", "2", "3", "4") and self.accepting:
            self.choose(int(key) - 1)
        elif key == "h" and self.session.is_practice and self.accepting:
            self.show_hint()
        elif key in ("return", "space") and self.waiting_for_next:
            self.go_on()

    # --- Startbildschirm ------------------------------------------------------

    def show_start_screen(self) -> None:
        self._new_screen()
        self.session = None
        c = self.canvas
        c.create_text(WIDTH / 2 + 3, 78, text="Waagen-Spiel", font=TITLE_FONT, fill=shade(BRASS, 0.4))
        c.create_text(WIDTH / 2, 75, text="Waagen-Spiel", font=TITLE_FONT, fill=INK)
        c.create_text(WIDTH / 2, 130, text="Schau dir die Waagen an und finde die schwerste Figur!",
                      font=(FONT, 15), fill=SOFT_INK)
        self._draw_logo()

        c.create_text(WIDTH / 2, 392, text="Schwierigkeit", font=(FONT, 14, "bold"), fill=INK)
        names = list(DIFFICULTIES)
        for i, name in enumerate(names):
            x = WIDTH / 2 + (i - (len(names) - 1) / 2) * 150
            self.button(x, 432, 136, 46, name, lambda n=name: self._select(difficulty=n), color="#3a86ff",
                        size=14, selected=name == self.difficulty)

        c.create_text(WIDTH / 2, 492, text="Zeit", font=(FONT, 14, "bold"), fill=INK)
        for i, seconds in enumerate(self.time_choices):
            x = WIDTH / 2 + (i - (len(self.time_choices) - 1) / 2) * 150
            label = "Üben" if seconds is None else f"{int(seconds)} Sekunden"
            self.button(x, 532, 136, 46, label, lambda s=seconds: self._select(time_limit=s), color="#9b5de5",
                        size=14, selected=seconds == self.time_limit)

        key = Highscores.key(self.difficulty, self.time_limit)
        best = self.highscores.get(key)
        note = "Üben: ohne Uhr, mit Tipps und Erklärungen" if self.time_limit is None else (
            f"Rekord: {best} Punkte" if best else "Noch kein Rekord – stell den ersten auf!")
        c.create_text(WIDTH / 2, 585, text=note, font=(FONT, 13), fill=SOFT_INK)
        self.button(WIDTH / 2, 645, 260, 64, "Los geht's!", self.start_game, color=GOOD, size=22)
        c.create_text(WIDTH / 2, 702, text="Figur anklicken oder Taste 1–4  ·  Enter: Start  ·  Esc: Menü",
                      font=(FONT, 11), fill=SOFT_INK)

    def _select(self, difficulty: str | None = None, time_limit: float | None | str = "unchanged") -> None:
        if difficulty is not None:
            self.difficulty = difficulty
        if time_limit != "unchanged":
            self.time_limit = time_limit  # type: ignore[assignment]
        self.show_start_screen()

    def _draw_logo(self) -> None:
        view = ScaleView(0, (0, 1), (2, 3, 0), 0)
        drawing = ScaleDrawing(self.canvas, WIDTH / 2, 170, view, self.preview, "logo", show_number=False)
        for i, ch in enumerate(self.preview):
            side = -1 if i < 2 else 1
            x = WIDTH / 2 + side * (250 + (i % 2) * 85)
            draw_character(self.canvas, x, 250 + (i % 2) * 30, 34, ch, ("logo",), mood="happy")
        start = self.generation

        def rock(t: float = 0.0) -> None:
            if start != self.generation:
                return
            drawing.set_angle(math.radians(7) * math.sin(t))
            self.later(40, lambda: rock(t + 0.08))

        rock()

    # --- Spiel ------------------------------------------------------------------

    def start_game(self) -> None:
        self.preview = pick_characters(random.Random())
        self.session = self.make_session(self.difficulty, self.time_limit, self.preview)
        self._new_screen(self._game_width())
        self.session.start()
        self._build_game_screen()
        self._show_round()
        self._tick()

    def _build_game_screen(self) -> None:
        c = self.canvas
        assert self.session is not None
        rounded_rect(c, 12, 10, WIDTH - 12, 58, 18, fill=PANEL, outline="#d7e3ee", width=2)
        self.status_text = c.create_text(32, 34, anchor="w", font=(FONT, 15, "bold"), fill=INK)
        self.points_text = c.create_text(WIDTH / 2 - 40, 34, font=(FONT, 17, "bold"), fill=BRASS_DARK)
        self.level_text = c.create_text(WIDTH / 2 + 120, 34, font=(FONT, 13), fill=SOFT_INK)
        if self.session.is_practice:
            self.button(WIDTH - 160, 34, 120, 36, "Tipp (H)", self.show_hint, color=GOLD, size=13)
            c.create_text(WIDTH - 40, 34, text="Üben", font=(FONT, 14, "bold"), fill="#9b5de5")
        else:
            self.time_text = c.create_text(WIDTH - 32, 34, anchor="e", font=(FONT, 17, "bold"), fill=INK)
            c.create_rectangle(12, 64, WIDTH - 12, 72, fill="#d7e3ee", outline="")
            self.time_bar = c.create_rectangle(12, 64, WIDTH - 12, 72, fill=GOOD, outline="")
        self.message = c.create_text(WIDTH / 2, 565, font=(FONT, 16, "bold"), fill=INK)
        self._update_header()

    def _update_header(self) -> None:
        s = self.session
        assert s is not None
        c = self.canvas
        c.itemconfigure(self.status_text, text=f"Runde {s.rounds + 1}    ✔ {s.correct}    ✘ {s.wrong}")
        c.itemconfigure(self.points_text, text=f"★ {s.points}")
        streak = f"    Serie {s.streak}" if s.streak >= 2 else ""
        c.itemconfigure(self.level_text, text=f"Stufe: {LEVEL_TITLES[s.difficulty.level]}{streak}")

    def _tick(self) -> None:
        s = self.session
        if s is None or s.is_practice:
            return
        left = s.time_left() or 0.0
        c = self.canvas
        c.itemconfigure(self.time_text, text=f"⏱ {math.ceil(left)} s", fill=BAD if left <= 10 else INK)
        share = left / float(s.time_limit or 1)
        c.coords(self.time_bar, 12, 64, 12 + (WIDTH - 24) * share, 72)
        c.itemconfigure(self.time_bar, fill=BAD if left <= 10 else (GOLD if share < 0.4 else GOOD))
        if s.is_over():
            self.later(150, self.show_end_screen)
            self.accepting = False
            return
        self.later(100, self._tick)

    def _show_round(self) -> None:
        s = self.session
        assert s is not None and s.current is not None
        self.round = s.current
        c = self.canvas
        for tag in ("scale", "marks", "cards", "panel", "float"):
            c.delete(tag)
        c.itemconfigure(self.message, text="Welche Figur ist am schwersten?", fill=SOFT_INK)
        self.drawings = []
        for view, (x, y) in zip(self.round.views, SCALE_SPOTS):
            tag = f"scale{view.number}"
            drawing = ScaleDrawing(c, x, y, view, s.characters, tag)
            c.addtag_withtag("scale", tag)
            self.drawings.append(drawing)
        self._draw_cards()
        self.hint_index = 0
        if s.is_practice:
            self._empty_panel()
        self.accepting = True
        self._animate_tilt()

    def _animate_tilt(self, frame: int = 0) -> None:
        t = frame / 30
        for d in self.drawings:
            d.set_angle(d.target_angle * (1 - math.exp(-5 * t) * math.cos(9 * t)) if t < 1 else d.target_angle)
        if t < 1:
            self.later(25, lambda: self._animate_tilt(frame + 1))

    def _draw_cards(self) -> None:
        s = self.session
        assert s is not None
        c = self.canvas
        self.cards: list[tuple[str, int, float, float]] = []
        for i, ch in enumerate(s.characters):
            x, y = WIDTH / 2 + (i - 1.5) * 190, 650
            tag = f"card{i}"
            rounded_rect(c, x - 78 + 3, y - 60 + 6, x + 78 + 3, y + 60 + 6, 22, fill="#c9d6e3", outline="",
                         tags=("cards", tag))
            body = rounded_rect(c, x - 78, y - 60, x + 78, y + 60, 22, fill=PANEL, outline="#c9d6e3", width=2,
                                tags=("cards", tag))
            draw_character(c, x, y - 10, 34, ch, ("cards", tag, f"{tag}_face"))
            c.create_text(x, y + 42, text=ch.name, font=(FONT, 13, "bold"), fill=INK, tags=("cards", tag))
            c.create_text(x - 60, y - 44, text=str(i + 1), font=(FONT, 11, "bold"), fill=SOFT_INK,
                          tags=("cards", tag))
            c.tag_bind(tag, "<Button-1>", lambda _e, i=i: self.choose(i) if self.accepting else None)
            c.tag_bind(tag, "<Enter>", lambda _e, b=body: (c.itemconfigure(b, outline=BRASS, width=4),
                                                            c.config(cursor="hand2")))
            c.tag_bind(tag, "<Leave>", lambda _e, b=body: (c.itemconfigure(b, outline="#c9d6e3", width=2),
                                                            c.config(cursor="")))
            self.cards.append((tag, body, x, y))

    def choose(self, choice: int) -> None:
        s, current = self.session, self.round
        if s is None or current is None or not self.accepting:
            return
        self.accepting = False
        feedback = s.answer(choice)
        self._update_header()
        if feedback.correct:
            self._celebrate(choice, feedback)
        else:
            self._reveal(choice, feedback)

    def _celebrate(self, choice: int, feedback: Feedback) -> None:
        c = self.canvas
        tag, body, x, y = self.cards[choice]
        c.itemconfigure(body, fill="#d8f3dc", outline=GOOD, width=4)
        c.delete(f"{tag}_face")
        draw_character(c, x, y - 10, 34, self.session.characters[choice], ("cards", tag, f"{tag}_face"),  # type: ignore[union-attr]
                       mood="happy")
        text = "Richtig!" + (f"  +{feedback.points}" if feedback.points else "")
        if feedback.level_after > feedback.level_before:
            text += f"   Neue Stufe: {LEVEL_TITLES[feedback.level_after]}!"
        elif feedback.streak >= 3:
            text += f"   {feedback.streak} in Folge!"
        c.itemconfigure(self.message, text=text, fill=GOOD)
        self._jump(f"{tag}_face")
        self._float_points(x, y - 70, f"+{feedback.points}")
        for d in self.drawings:
            d.mark(choice, GOOD)
        self.later(750, self._next_round)

    def _jump(self, tag: str, frame: int = 0) -> None:
        offsets = [-6, -6, -5, -3, 0, 3, 5, 6, 6]
        if frame < len(offsets):
            self.canvas.move(tag, 0, offsets[frame])
            self.later(25, lambda: self._jump(tag, frame + 1))

    def _float_points(self, x: float, y: float, text: str, frame: int = 0) -> None:
        c = self.canvas
        if frame == 0:
            self._float_id = c.create_text(x, y, text=text, font=(FONT, 20, "bold"), fill=GOLD, tags=("float",))
        elif frame < 18:
            c.move(self._float_id, 0, -2.5)
        else:
            c.delete(self._float_id)
            return
        self.later(30, lambda: self._float_points(x, y, text, frame + 1))

    def _reveal(self, choice: int, feedback: Feedback) -> None:
        s = self.session
        assert s is not None and self.round is not None
        c = self.canvas
        _tag, wrong_body, _x, _y = self.cards[choice]
        c.itemconfigure(wrong_body, fill="#ffe3e6", outline=BAD, width=4)
        self._shake(self.cards[choice][0])
        right_tag, right_body, rx, ry = self.cards[feedback.answer]
        c.itemconfigure(right_body, fill="#fff3c4", outline=GOLD, width=5)
        ring = c.create_oval(rx - 42, ry - 52, rx + 42, ry + 32, outline=GOLD, width=5, tags=("cards",))
        self._pulse(ring)
        for d in self.drawings:
            d.mark(feedback.answer, GOLD)
        right, wrong = s.characters[feedback.answer].name, s.characters[choice].name
        c.itemconfigure(self.message, text=f"Leider nicht – {right} ist am schwersten.", fill=BAD)
        if s.is_practice:
            lines = [explain_with_names(line, s.characters) for line in self.round.why_lighter(choice)]
            self._panel(f"Warum ist {wrong} leichter als {right}?", lines)
            self._wait_for_next()
        else:
            self.later(1000, self._next_round)

    def _shake(self, tag: str, frame: int = 0) -> None:
        offsets = [-7, 14, -14, 12, -10, 8, -3]
        if frame < len(offsets):
            self.canvas.move(tag, offsets[frame], 0)
            self.later(30, lambda: self._shake(tag, frame + 1))

    def _pulse(self, ring: int, frame: int = 0) -> None:
        if frame < 40:
            self.canvas.itemconfigure(ring, width=3 + 3 * abs(math.sin(frame / 3)))
            self.later(50, lambda: self._pulse(ring, frame + 1))

    def _panel(self, title: str, lines: Sequence[str]) -> None:
        """Tipp-Leiste rechts neben dem Spielfeld (nur im Uebungsmodus)."""

        c = self.canvas
        c.delete("panel")
        x0, x1, top, bottom = WIDTH, WIDTH + SIDEBAR - 14, 10, HEIGHT - 12
        rounded_rect(c, x0, top, x1, bottom, 18, fill=PANEL, outline=GOLD, width=3, tags=("panel",))
        c.create_text(x0 + 18, top + 18, anchor="nw", text=title, font=(FONT, 14, "bold"), fill=INK,
                      width=x1 - x0 - 36, tags=("panel",))
        heading = c.bbox(c.find_withtag("panel")[-1])[3]
        text = "\n".join(f"• {line}" for line in lines)
        c.create_text(x0 + 18, heading + 12, anchor="nw", text=text, font=(FONT, 12), fill=INK,
                      width=x1 - x0 - 36, tags=("panel",))

    def _empty_panel(self) -> None:
        self._panel("Tipps", ["Weißt du nicht weiter? Drück H oder den Tipp-Knopf.",
                              "Dann zeige ich dir Schritt für Schritt, wie man die schwerste Figur findet."])

    def show_hint(self) -> None:
        s = self.session
        if s is None or self.round is None or not self.accepting:
            return
        hints = self.round.hints()
        if not hints:
            return
        step = hints[min(self.hint_index, len(hints) - 1)]
        title = f"Tipp {min(self.hint_index, len(hints) - 1) + 1} von {len(hints)}"
        self._panel(title, [explain_with_names(line, s.characters) for line in step])
        self.hint_index += 1

    def _wait_for_next(self) -> None:
        self.waiting_for_next = True
        self.button(WIDTH / 2, 565, 220, 40, "Weiter (Enter)", self.go_on, color=GOOD, size=14)
        self.canvas.itemconfigure(self.message, text="")

    def go_on(self) -> None:
        if not self.waiting_for_next:
            return
        self.waiting_for_next = False
        self._new_screen_keep_session()

    def _game_width(self) -> int:
        return WIDTH + SIDEBAR if self.session is not None and self.session.is_practice else WIDTH

    def _new_screen_keep_session(self) -> None:
        self._new_screen(self._game_width())
        self._build_game_screen()
        self._next_round()

    def _next_round(self) -> None:
        s = self.session
        if s is None:
            return
        if s.is_over():
            self.show_end_screen()
            return
        s.next_round()
        self._update_header()
        self._show_round()

    # --- Auswertung -------------------------------------------------------------

    def show_end_screen(self) -> None:
        s = self.session
        if s is None:
            return
        result = s.result()
        key = Highscores.key(self.difficulty, self.time_limit)
        old_best = self.highscores.get(key)
        record = not s.is_practice and self.highscores.submit(key, result.points)
        self._new_screen()
        self.session = None
        c = self.canvas
        title = "Gut geübt!" if s.is_practice else ("Zeit ist um!" if s.is_over() else "Spiel beendet")
        c.create_text(WIDTH / 2, 90, text=title, font=TITLE_FONT, fill=INK)
        if record:
            c.create_text(WIDTH / 2, 150, text="★ Neuer Rekord! ★", font=(FONT, 22, "bold"), fill=BRASS_DARK)
        elif old_best:
            c.create_text(WIDTH / 2, 150, text=f"Rekord: {old_best} Punkte", font=(FONT, 16), fill=SOFT_INK)
        rows = [
            ("Gespielte Runden", str(result.rounds), INK),
            ("Richtig gelöst", str(result.correct), GOOD),
            ("Falsch", str(result.wrong), BAD),
            ("Beste Serie", str(result.best_streak), INK),
            ("Punkte", str(result.points), BRASS_DARK),
        ]
        rounded_rect(c, WIDTH / 2 - 230, 190, WIDTH / 2 + 230, 470, 26, fill=PANEL, outline="#d7e3ee", width=2)
        for i, (label, value, color) in enumerate(rows):
            y = 230 + i * 52
            c.create_text(WIDTH / 2 - 190, y, text=label, anchor="w", font=(FONT, 17), fill=INK)
            c.create_text(WIDTH / 2 + 190, y, text=value, anchor="e", font=(FONT, 22, "bold"), fill=color)
        for i, ch in enumerate(self.preview):
            x = WIDTH / 2 + (i - 1.5) * 120
            draw_character(c, x, 535, 30, ch, (), mood="happy" if result.correct >= result.wrong else "wow")
        self.button(WIDTH / 2 - 140, 640, 240, 60, "Nochmal (Enter)", self.start_game, color=GOOD, size=17)
        self.button(WIDTH / 2 + 140, 640, 240, 60, "Menü (Esc)", self.show_start_screen, color="#3a86ff", size=17)
        if record:
            self._confetti()

    def _confetti(self) -> None:
        c = self.canvas
        rng = random.Random()
        pieces = []
        for _ in range(70):
            x, y = rng.uniform(0, WIDTH), rng.uniform(-300, 0)
            color = rng.choice(["#ef476f", "#ffd23f", "#06d6a0", "#3a86ff", "#9b5de5", "#ff8c42"])
            item = c.create_rectangle(x, y, x + 8, y + 12, fill=color, outline="")
            pieces.append((item, rng.uniform(3, 7), rng.uniform(-1.5, 1.5)))

        def fall(frame: int = 0) -> None:
            for item, vy, vx in pieces:
                c.move(item, vx + math.sin(frame / 5 + vy), vy)
            if frame < 120:
                self.later(30, lambda: fall(frame + 1))
            else:
                for item, _vy, _vx in pieces:
                    c.delete(item)

        fall()
