// SVG-Zeichnungen: Figuren und Waagen (nur Darstellung, keine Spiellogik).

import { panPositions } from "./spiel.js";

const NS = "http://www.w3.org/2000/svg";
export const BRASS = "#e0a526";
export const BRASS_DARK = "#9c6b00";

export function el(name, attrs = {}, parent = null) {
  const node = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.appendChild(node);
  return node;
}

export function shade(color, factor) {
  const rgb = [1, 3, 5].map((i) => parseInt(color.slice(i, i + 2), 16));
  const mixed = rgb.map((v) => Math.round(factor >= 0 ? v + (255 - v) * factor : v * (1 + factor)));
  return "#" + mixed.map((v) => v.toString(16).padStart(2, "0")).join("");
}

function roundedPolygon(points, t = 0.22) {
  // Ecken als quadratische Kurven: sanft gerundetes Vieleck
  const n = points.length;
  const lerp = (p, q, s) => [p[0] + (q[0] - p[0]) * s, p[1] + (q[1] - p[1]) * s];
  let d = "";
  for (let i = 0; i < n; i++) {
    const prev = points[(i + n - 1) % n];
    const cur = points[i];
    const next = points[(i + 1) % n];
    const a = lerp(cur, prev, t);
    const b = lerp(cur, next, t);
    d += `${i ? "L" : "M"}${a[0]},${a[1]} Q${cur[0]},${cur[1]} ${b[0]},${b[1]} `;
  }
  return d + "Z";
}

/** Eine Figur: schlichte Form mit dunklerem Rand, Mittelpunkt (0, 0), Radius r. */
export function character(ch, r) {
  const g = el("g", { class: "figur" });
  const common = {
    fill: ch.color,
    stroke: shade(ch.color, -0.35),
    "stroke-width": Math.max(1.5, r / 9),
    "stroke-linejoin": "round",
  };
  if (ch.shape === "kreis") {
    el("circle", { r, ...common }, g);
  } else if (ch.shape === "quadrat") {
    el("rect", { x: -0.9 * r, y: -0.9 * r, width: 1.8 * r, height: 1.8 * r, rx: 0.3 * r, ...common }, g);
  } else if (ch.shape === "dreieck") {
    el("path", { d: roundedPolygon([[0, -1.15 * r], [1.12 * r, 0.9 * r], [-1.12 * r, 0.9 * r]], 0.12), ...common }, g);
  } else {
    const k = 0.88 * r;
    el("path", {
      d: `M0,${-1.22 * r} C${0.3 * r},${-0.75 * r} ${k},${-0.4 * r} ${k},${0.2 * r} A${k} ${k} 0 0 1 ${-k},${0.2 * r} C${-k},${-0.4 * r} ${-0.3 * r},${-0.75 * r} 0,${-1.22 * r} Z`,
      ...common,
    }, g);
  }
  return g;
}

/** SVG-Element (eigene Leinwand) mit einer Figur, z. B. fuer Antwortknoepfe. */
export function characterIcon(ch) {
  const svg = el("svg", { viewBox: "-40 -40 80 80", class: "figur-icon", "aria-hidden": "true" });
  svg.appendChild(character(ch, 30));
  return svg;
}

/** Eine Balkenwaage; set(angle) neigt sie, mark(who, color) umringt Figuren. */
export class ScaleDrawing {
  static ARM = 76;
  static DROP = 72;
  static PAN = 38;
  static ITEM = 16;
  static MAX_ANGLE = (11 * Math.PI) / 180;

  constructor(parent, x, y, view, characters, { showNumber = true } = {}) {
    const { ARM, DROP, PAN, ITEM } = ScaleDrawing;
    this.x = x;
    this.y = y;
    this.view = view;
    this.angle = 0;
    const g = (this.group = el("g", { class: "waage" }, parent));
    el("polygon", { points: `${x - 40},${y + 104} ${x + 40},${y + 104} ${x + 23},${y + 91} ${x - 23},${y + 91}`,
      fill: BRASS, stroke: BRASS_DARK, "stroke-width": 1.6, "stroke-linejoin": "round" }, g);
    el("rect", { x: x - 4.5, y, width: 9, height: 92, fill: BRASS, stroke: BRASS_DARK, "stroke-width": 1.6 }, g);
    if (showNumber) {
      el("circle", { cx: x, cy: y + 62, r: 11, fill: "white", stroke: BRASS_DARK, "stroke-width": 1.6 }, g);
      const t = el("text", { x, y: y + 66.5, "text-anchor": "middle", class: "waage-nr" }, g);
      t.textContent = view.number;
    }
    this.beam = el("line", { stroke: BRASS, "stroke-width": 6.5, "stroke-linecap": "round" }, g);
    this.sides = [view.left, view.right].map((items) => {
      const strings = [0, 1].map(() => el("line", { stroke: BRASS_DARK, "stroke-width": 1.3 }, g));
      const pan = el("g", {}, g);
      const positions = panPositions(items.length);
      const placed = items.map((who, i) => {
        const [offset, row] = positions[i];
        const ix = offset * 2.05 * ITEM;
        const iy = DROP - ITEM - 1.5 - row * 1.72 * ITEM;
        const fig = character(characters[who], ITEM);
        fig.setAttribute("transform", `translate(${ix},${iy})`);
        pan.appendChild(fig);
        return { who, ix, iy };
      });
      el("path", { d: `M${-PAN},${DROP} L${PAN},${DROP} L${PAN - 8},${DROP + 10} L${-PAN + 8},${DROP + 10} Z`,
        fill: BRASS, stroke: BRASS_DARK, "stroke-width": 1.6, "stroke-linejoin": "round" }, pan);
      return { strings, pan, placed };
    });
    el("circle", { cx: x, cy: y, r: 7, fill: BRASS, stroke: BRASS_DARK, "stroke-width": 1.6 }, g);
    this.set(0);
  }

  get targetAngle() {
    return this.view.tilt * ScaleDrawing.MAX_ANGLE;
  }

  ends(angle) {
    const dx = ScaleDrawing.ARM * Math.cos(angle);
    const dy = ScaleDrawing.ARM * Math.sin(angle);
    return [[this.x - dx, this.y - dy], [this.x + dx, this.y + dy]];
  }

  set(angle) {
    const { DROP, PAN } = ScaleDrawing;
    this.angle = angle;
    const ends = this.ends(angle);
    const [[lx, ly], [rx, ry]] = ends;
    Object.entries({ x1: lx, y1: ly, x2: rx, y2: ry }).forEach(([k, v]) => this.beam.setAttribute(k, v));
    this.sides.forEach(({ strings, pan }, side) => {
      const [ex, ey] = ends[side];
      [-1, 1].forEach((dir, i) => {
        const s = strings[i];
        s.setAttribute("x1", ex);
        s.setAttribute("y1", ey);
        s.setAttribute("x2", ex + dir * (PAN - 5));
        s.setAttribute("y2", ey + DROP);
      });
      pan.setAttribute("transform", `translate(${ex},${ey})`);
    });
  }

  mark(who, cls) {
    for (const { pan, placed } of this.sides) {
      for (const item of placed) {
        if (item.who === who) {
          el("circle", { cx: item.ix, cy: item.iy, r: ScaleDrawing.ITEM + 5, class: `ring ${cls}` }, pan);
        }
      }
    }
  }
}

/** Neigt Waagen gedaempft schwingend in ihre Lage (etwa 0,75 s). */
export function animateTilt(drawings, done = () => {}) {
  const start = performance.now();
  const frame = (now) => {
    const t = Math.min(1, (now - start) / 750);
    for (const d of drawings) d.set(t < 1 ? d.targetAngle * (1 - Math.exp(-5 * t) * Math.cos(9 * t)) : d.targetAngle);
    if (t < 1) requestAnimationFrame(frame);
    else done();
  };
  requestAnimationFrame(frame);
}
