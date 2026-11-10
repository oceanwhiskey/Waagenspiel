# Vereinfachte Herleitung

Dieses Dokument ist eine schlanke Alternative zu `01_formalisierung.md` und
`02_algorithmus.md`. Die dortigen Aussagen sind korrekt, beantworten aber eine
schwerere Frage, als das Waagenspiel stellt. Hier wird gezeigt, dass der Kern
des Problems mit wenig Mathematik auskommt: lineare Ungleichungen in vier
Variablen, ein kleines lineares Programm und das Farkas-Lemma.

## 1. Festlegungen

Die README lässt einige Punkte offen. Hier gelten die folgenden Festlegungen,
jeweils mit der verworfenen Alternative.

| Frage | Festlegung hier | Alternative (in `01`/`02`) |
|---|---|---|
| Wann sind zwei Systeme gleich? | Wenn sie bis auf Umbenennung aus denselben Waagen bestehen (syntaktisch). | Wenn sie bis auf Umbenennung dieselbe Lösungsmenge haben (semantisch). |
| Was heißt „kein Mehrwert“? | Ohne die Waage ist das schwerste Element nicht mehr eindeutig (Zielminimalität). | Ohne die Waage wird die Lösungsmenge größer (Informationsminimalität). |
| Müssen die Gewichte verschieden sein? | Nein, nur $a$ muss echt am schwersten sein. | Ja, alle vier paarweise verschieden. |

Begründung: Für einen Spieler sind zwei Rätsel mit verschiedenen Waagen
verschiedene Rätsel, auch wenn man aus beiden dasselbe folgern kann. Und eine
Waage, die man zum Finden des Schwersten nicht braucht, ist im Spiel
überflüssig, selbst wenn sie formal Information enthält. Gleichgewichte wie
$b = c$ sind im Spiel natürlich, deshalb werden gleiche Gewichte unter den
leichteren Gegenständen erlaubt. Abschnitt 4.3 zeigt, dass diese letzte Wahl
den Entscheidungstest nicht verändert.

## 2. Modell

Die Gewichte bilden einen Vektor

$$
w = (w_a, w_b, w_c, w_d), \qquad w_v > 0 \text{ für alle } v.
$$

Eine Seite einer Waage ist eine Multimenge von Gegenständen, also ein Vektor
$m \in \mathbb N_0^4$ mit $1 \le \sum_v m_v \le 3$. Eine Waage mit linker
Seite $L$ und rechter Seite $R$ (ohne gemeinsame Gegenstände) wird zum Vektor

$$
z = L - R \in \mathbb Z^4 .
$$

- Neigt sie sich nach rechts ($L$ leichter als $R$), gilt $z \cdot w < 0$.
- Ist sie im Gleichgewicht, gilt $z \cdot w = 0$.

Eine Waage mit $L$ schwerer als $R$ wird durch Vertauschen der Seiten zur
ersten Form. Ein System $s$ besteht also aus strikten Zeilen $z_1,\dots,z_p$
und Gleichungszeilen $y_1,\dots,y_q$.

### 2.1 Ganze oder reelle Zahlen ist egal

Alle Bedingungen sind homogen: Ist $w$ eine Lösung, dann auch $t w$ für jedes
$t > 0$. Die Lösungsmenge ist ein relativ offener Kegel, der durch ganzzahlige
Daten beschrieben wird. Hat er einen reellen Punkt, so liegen dort auch
rationale Punkte (sie liegen dicht), und Multiplikation mit dem Hauptnenner
liefert eine ganzzahlige Lösung. Man darf daher überall reell rechnen.

Eine numerisch eindeutige Lösung kann es wegen der Skalierung nie geben.
„Eindeutige Lösung“ heißt im Spiel deshalb: Das schwerste Element ist
eindeutig bestimmt.

## 3. Wann ist $a$ eindeutig am schwersten?

**Satz 1.** $a$ ist durch $s$ eindeutig als schwerstes Element bestimmt genau
dann, wenn $s$ erfüllbar ist und für jedes $x \in \{b, c, d\}$ das System

$$
s \;\land\; w > 0 \;\land\; w_x \ge w_a
$$

keine Lösung hat.

Das ist nur die Definition: Es gibt keine erlaubte Belegung, in der ein
anderer Gegenstand mindestens so schwer ist wie $a$.

### 3.1 Als lineares Programm

Wegen der Homogenität kann man jeden strikten Abstand auf mindestens $1$
hochskalieren. Das System aus Satz 1 ist daher genau dann lösbar, wenn das
folgende lineare Programm zulässig ist:

$$
w_v \ge 1 \;(v \in \{a,b,c,d\}), \qquad
z_i \cdot w \le -1, \qquad
y_j \cdot w = 0, \qquad
w_x - w_a \ge 0 .
$$

Pro System sind das **drei** Zulässigkeitstests mit je vier Variablen, dazu
einer für die Erfüllbarkeit ohne die letzte Zeile. Jeder LP-Löser und jeder
SMT-Löser (z. B. Z3 mit `Real`-Variablen) erledigt das sofort; siehe Anhang.

### 3.2 Der Lösungsweg: Farkas-Lemma

Die strikten Bedingungen sind die Waagen $z_i$ und die Positivität, die man als
$-e_v \cdot w < 0$ schreibt. Zusammen heißen sie $\alpha_1, \dots, \alpha_k$.

**Satz 2.** Sei $s$ erfüllbar. Dann folgt $w_x < w_a$ aus $s$ genau dann, wenn
es Zahlen $\lambda_1,\dots,\lambda_k \ge 0$, nicht alle null, und beliebige
$\mu_1, \dots, \mu_q$ gibt mit

$$
e_x - e_a = \sum_i \lambda_i \alpha_i + \sum_j \mu_j y_j .
$$

In Worten: Man addiert Waagen mit nichtnegativen Faktoren (Gleichgewichte
dürfen auch abgezogen werden) und streicht danach Gegenstände auf der leichten
Seite, weil sie positiv wiegen, bis $x < a$ dasteht. Genau so rechnet auch ein
Mensch.

*Beweis.* „$\Leftarrow$“: Die rechte Seite ist, angewandt auf eine Lösung $w$,
eine Summe nichtpositiver Terme mit mindestens einem echt negativen Term und
mehreren Nullen, also $< 0$.

„$\Rightarrow$“: Folgt $w_x < w_a$, dann ist das System
$\alpha_i \cdot w < 0$, $y_j \cdot w = 0$, $-(e_x - e_a)\cdot w \le 0$
unlösbar. Nach dem Transpositionssatz von Motzkin gibt es $\lambda \ge 0$ mit
$\lambda \ne 0$, $\nu \ge 0$ und $\mu$ mit

$$
\sum_i \lambda_i \alpha_i - \nu\,(e_x - e_a) + \sum_j \mu_j y_j = 0 .
$$

Wäre $\nu = 0$, so wäre schon $s$ unlösbar, was ausgeschlossen ist. Division
durch $\nu > 0$ liefert die behauptete Darstellung. $\square$

Die Faktoren $\lambda, \mu$ sind ein **Zertifikat**: Ein LP-Löser liefert sie
als duale Lösung, und das Trainingsspiel kann daraus einen Lösungsweg oder
Hinweis erzeugen, ohne eigene Logik.

### 3.3 Beispiel

Das System

$$
3d < 2a + c, \qquad b + c < a
$$

hat die Zeilen $z_1 = (-2, 0, -1, 3)$ und $z_2 = (-1, 1, 1, 0)$ in der
Reihenfolge $(a, b, c, d)$.

- $b < a$: $z_2 + (-e_c) = e_b - e_a$. In Worten: In $b + c < a$ streicht man $c$.
- $c < a$: $z_2 + (-e_b) = e_c - e_a$.
- $d < a$: $\tfrac13 z_1 + \tfrac13 z_2 + \tfrac13(-e_b) = e_d - e_a$.
  In Worten: Beide Waagen addieren ergibt $3d + b + c < 3a + c$. Kürzen von
  $c$ und Streichen von $b$ ergibt $3d < 3a$, also $d < a$.

Also ist $a$ eindeutig am schwersten.

### 3.4 Sonderfall: ein Gegenstand pro Seite

Stehen auf jeder Seite nur einzelne Gegenstände ($x < y$ oder $x = y$), ist das
Problem reine Graphentheorie. Man fasst durch Gleichgewichte verbundene
Gegenstände zu Klassen zusammen und zeichnet für jedes $x < y$ einen Pfeil von
$y$ nach $x$.

**Satz 3.** $a$ ist eindeutig am schwersten genau dann, wenn der Graph
kreisfrei ist, die Klasse von $a$ nur $a$ enthält und von $a$ aus jede andere
Klasse über Pfeile erreichbar ist.

*Beweis.* „$\Leftarrow$“ ist Transitivität. „$\Rightarrow$“: Ist die Klasse
von $x$ von $a$ aus nicht erreichbar, sei $U$ die Menge der Klassen, von denen
aus $x$ erreichbar ist (inklusive der von $x$). Dann gilt $a \notin U$. Man
wähle Gewichte $h$ passend zu einer topologischen Sortierung und addiere eine
große Konstante $M$ auf alle Klassen in $U$. Jeder Pfeil, der in $U$ endet,
beginnt auch in $U$, also bleiben alle Waagen erfüllt, aber für großes $M$ gilt
$w_x > w_a$. $\square$

## 4. Gleichheit, Minimalität, Benennung

### 4.1 Normalform und Gleichheit

Eine Waage wird normalisiert, indem man

1. gemeinsame Gegenstände auf beiden Seiten kürzt (README Punkt 4),
2. bei $<$ die leichte Seite nach links stellt,
3. bei $=$ die beiden Seiten in einer festen Reihenfolge anordnet, z. B. die
   lexikographisch kleinere links.

Optional kann man zusätzlich durch den ggT teilen, sodass $2a < 2b$ und
$a < b$ zusammenfallen. Für das Spiel ist das nicht nötig, weil es zwei
optisch verschiedene Waagen sind.

Ein System ist die **Menge** seiner normalisierten Waagen. Sein Schlüssel ist

$$
\operatorname{key}(s) = \min_{\pi} \operatorname{sort}\bigl(\operatorname{NF}(\pi s)\bigr),
$$

wobei $\pi$ über die sechs Umbenennungen von $b, c, d$ läuft ($a$ ist als
Schwerster schon festgelegt). Zwei Systeme sind gleich genau dann, wenn ihre
Schlüssel gleich sind. Das ist reines Sortieren, keine Geometrie.

### 4.2 Keine überflüssige Waage

$s$ heißt **zielminimal**, wenn für jede Waage $r \in s$ gilt: $s \setminus
\{r\}$ bestimmt $a$ nicht mehr eindeutig als Schwersten. Das sind höchstens
$3 \cdot 3 = 9$ weitere LP-Tests.

Zielminimal ist stärker als informationsminimal: Folgt $r$ aus den übrigen
Waagen, dann bestimmen diese auch ohne $r$ den Schwersten, also ist ein
zielminimales System automatisch informationsminimal. Die Umkehrung gilt
nicht, siehe Abschnitt 5.

### 4.3 Verschiedene Gewichte ändern den Test nicht

Würde man paarweise verschiedene Gewichte fordern, müsste man in Satz 1
$w_x > w_a$ statt $w_x \ge w_a$ testen. Der Unterschied tritt nur auf, wenn
die Lösungsmenge ganz in der Hyperebene $w_x = w_a$ liegt: Eine lineare
Funktion, die auf einer relativ offenen Menge $\le 0$ ist und den Wert $0$
annimmt, ist dort konstant null. Dann ist $a$ aber ohnehin nicht echt am
schwersten. Die Forderung verschiedener Gewichte entfernt also nur Systeme, in
denen Gleichgewichte zwei Gegenstände gleich schwer machen, z. B. $b = c$.

### 4.4 Punkt 6 der README

Die Bedingung „aus $s$ folgt nie $b > c$, $d > c$ oder $d > b$“ legt nur fest,
wie $b, c, d$ benannt werden. Für die Verschiedenheit der Systeme sorgt schon
das Minimum über die Umbenennungen in Abschnitt 4.1. Man kann die Konvention
für die Ausgabe zusätzlich erfüllen: Die erzwungenen Vergleiche unter
$b, c, d$ bilden eine Halbordnung, und benennt man eine lineare Erweiterung
von groß nach klein mit $c, b, d$, folgt keiner der drei verbotenen
Vergleiche.

## 5. Abgleich mit `data/systems-pairs.json`

Ein Prüfskript nach Abschnitt 3.1 (siehe Anhang) bestätigt für alle 503
Zweiersysteme im JSON, dass $a$ eindeutig am schwersten ist. In **96** davon
reicht aber eine Waage allein, sie sind also nicht zielminimal. Beispiele:

```text
3d < 2a + c   ;  b + c + d < a
3d < 2a       ;  b + c + d < a
2d < a + 2c   ;  b + c + d < a
```

Die zweite Waage bestimmt den Schwersten jeweils schon allein. Die erste
liefert zwar zusätzliche Information über $d$, hilft beim Finden des
Schwersten aber nicht.

## 6. Folgerung für das Trainingsspiel

Für ein Trainingsspiel muss die Menge $S$ nicht vollständig aufgezählt werden.
Rätsel lassen sich direkt erzeugen:

1. Ziehe zufällige positive Gewichte mit echtem Maximum bei $a$.
2. Ziehe zufällige Waagen (Seiten mit 1 bis 3 Gegenständen) und lies ihr
   Ergebnis an den Gewichten ab. Dadurch ist das System automatisch erfüllbar.
3. Prüfe mit Satz 1, ob $a$ eindeutig am schwersten ist, und mit 4.2, ob das
   System zielminimal ist. Sonst verwerfen und neu ziehen.
4. Benenne die Gegenstände zufällig um und zeige sie als Bilder.
5. Speichere die Schlüssel aus 4.1, um Wiederholungen zu vermeiden.
6. Zeige bei Bedarf das Farkas-Zertifikat aus 3.2 als Lösungsweg.

Die Schwierigkeit lässt sich über die Anzahl der Gegenstände pro Seite, die
Anzahl der Waagen und die Größe der Faktoren $\lambda$ im Zertifikat steuern.
Ein Rätsel, dessen Zertifikat nur Streichen braucht, ist leicht; eines, bei dem
man Waagen addieren muss, ist schwer.

## 7. Umsetzung

Die Abschnitte 3 bis 6 sind in `src/waagenspiel/puzzle.py` umgesetzt, die
Kommandozeile in `raetsel.py`:

```bash
python raetsel.py erzeugen --anzahl 20 --stufe mittel --ausgabe data/raetsel.json
python raetsel.py erzeugen --anzahl 5 --stufe schwer --mit-loesung
python raetsel.py spielen --stufe leicht
```

| Baustein | Funktion | Abschnitt |
|---|---|---|
| Waage in Normalform | `Scale` | 2, 4.1 |
| Eindeutig Schwerster | `heaviest`, `forces_heaviest` | 3, 3.1 |
| Lösungsweg | `derive`, `explain`, `Derivation.steps` | 3.2 |
| Gleichheit | `canonical_form` | 4.1 |
| Keine überflüssige Waage | `is_minimal` | 4.2 |
| Generator | `PuzzleGenerator` | 6 |

Ergänzungen gegenüber Abschnitt 6:

- **Schneller Vorfilter.** Bevor Z3 gefragt wird, werden 600 feste
  Zufallsgewichte eingesetzt. Erfüllt eines davon alle Waagen und hat einen
  anderen Schwersten, ist das Rätsel sicher widerlegt. Bewiesen wird die
  Eindeutigkeit immer exakt mit Z3.
- **Keine vervielfachten Waagen.** Waagen wie $2c < 2a$ oder $3c = 3d$ werden
  nicht erzeugt (ggT der Koeffizienten größer als 1). Sie sind nur verkleidete
  einfachere Waagen. Mit `Settings(allow_multiples=True)` lassen sie sich
  zulassen.
- **Schwierigkeit.** Für jeden der drei Vergleiche mit dem Schwersten wird
  zuerst die kleinste Teilmenge der Waagen gesucht, die ihn erzwingt, und auf
  ihr ein Farkas-Zertifikat mit möglichst kleiner Faktorsumme. Die
  Schwierigkeit ist die größte Zahl addierter Waagen. Das ist eine Faustregel,
  kein bewiesenes Minimum.
- **Stufen.** `leicht`: ein Gegenstand pro Seite und drei Waagen (mit zwei
  geht es nach Satz 3 nicht). `mittel`: bis zu zwei Gegenstände pro Seite,
  Schwierigkeit höchstens 2. `schwer`: bis zu drei Gegenstände pro Seite,
  Schwierigkeit 3 bis 6. Ohne Obergrenze entstehen korrekte, aber kaum von Hand
  lösbare Rätsel mit über zehn addierten Waagen.
- **Ausgabe.** Rätsel werden kanonisch gespeichert, also immer mit $a$ als
  Schwerstem. Im Spielmodus werden Namen und Reihenfolge der Waagen zufällig
  gemischt.

## Anhang: Prüfskript

```python
from z3 import Reals, Solver, Sum, sat

w = dict(zip("abcd", Reals("a b c d")))

def side(m):
    return Sum([k * w[v] for v, k in m.items()])

def relation(r):
    left, right = side(r["left"]), side(r["right"])
    return left < right if r["operator"] == "<" else left == right

def heaviest_is_a(relations):
    """Satz 1: a ist eindeutig am schwersten."""
    base = [v > 0 for v in w.values()] + [relation(r) for r in relations]
    s = Solver(); s.add(*base)
    if s.check() != sat:
        return False
    for x in "bcd":
        s = Solver(); s.add(*base, w[x] >= w["a"])
        if s.check() == sat:
            return False
    return True

def goal_minimal(relations):
    """Abschnitt 4.2: jede Waage wird gebraucht."""
    return heaviest_is_a(relations) and not any(
        heaviest_is_a(relations[:i] + relations[i + 1:])
        for i in range(len(relations))
    )
```

Die Relationen haben dasselbe Format wie in `data/systems-pairs.json`, also
`{"left": {"b": 1, "c": 1}, "operator": "<", "right": {"a": 1}}`.
