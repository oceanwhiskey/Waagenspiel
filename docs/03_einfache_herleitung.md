# Vereinfachte Herleitung

Ein erster Versuch (inzwischen gelöscht) hatte eine schwerere Frage
beantwortet, als das Waagenspiel stellt. Hier wird gezeigt, dass der Kern
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
Noch schneller geht es ohne allgemeinen Löser über die Kantenstrahlen des
Lösungskegels (Abschnitt 11).

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

## 5. Abgleich mit dem ersten Versuch

Der erste, inzwischen gelöschte Versuch hatte 503 Zweiersysteme erzeugt. Ein
Prüfskript nach Abschnitt 3.1 (siehe Anhang) bestätigte für alle, dass $a$
eindeutig am schwersten ist. In **96** davon reichte aber eine Waage allein,
sie waren also nicht zielminimal. Beispiele:

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

Die Schwierigkeit wird über die Anzahl der Gegenstände pro Seite und die
Stufe aus Abschnitt 8 gesteuert.

## 7. Umsetzung

Die Abschnitte 3 bis 6 und 8 sind in `src/waagenspiel/puzzle.py` umgesetzt,
der Katalog (Abschnitt 9) in `src/waagenspiel/catalog.py` und `katalog.py`,
der Baukasten (Abschnitt 10) in `src/waagenspiel/construct.py`. Die
Kommandozeile ist `raetsel.py`:

```bash
python raetsel.py erzeugen --anzahl 20 --stufe mittel --ausgabe data/raetsel.json
python raetsel.py erzeugen --anzahl 5 --stufe experte --mit-loesung
python raetsel.py spielen --stufe leicht
python raetsel.py spielen --stufe schwer --quelle baukasten
```

`--quelle` wählt, woher die Rätsel kommen: `katalog` (Standard,
gleichverteilt aus allen Rätseln), `baukasten` (gezielt gebaut, Stufen 1 bis
3) oder `zufall` (blind gezogen und geprüft, Abschnitt 6).

| Baustein | Funktion | Abschnitt |
|---|---|---|
| Waage in Normalform | `Scale` | 2, 4.1 |
| Eindeutig Schwerster | `heaviest`, `forces_heaviest` | 3, 3.1 |
| Lösungsweg eines Vergleichs | `derive`, `Derivation.steps` | 3.2 |
| Lösen in Schritten, Stufe | `solve`, `Solution`, `Step` | 8 |
| Gleichheit | `canonical_form` | 4.1 |
| Keine überflüssige Waage | `is_minimal` | 4.2 |
| Zufallsgenerator | `PuzzleGenerator` | 6 |
| Katalog | `build_catalog`, `CatalogSource` | 9 |
| Baukasten | `Knowledge`, `ConstructiveGenerator` | 10 |

Ergänzungen gegenüber Abschnitt 6:

- **Löser.** Alle Prüfungen nach Satz 1 laufen über den exakten
  Strahlen-Löser aus Abschnitt 11. Z3 wird nur noch für die Faktoren der
  Lösungswege (3.2), für die kleinsten Beispielgewichte und als Referenz in
  den Tests gebraucht.
- **Keine vervielfachten Waagen.** Waagen wie $2c < 2a$ oder $3c = 3d$ werden
  nicht erzeugt (ggT der Koeffizienten größer als 1). Sie sind nur verkleidete
  einfachere Waagen. Mit `Settings(allow_multiples=True)` lassen sie sich
  zulassen.
- **Spielstufen.** Jedes Rätsel hat zwei oder drei Waagen.

  | `--stufe` | Gegenstände pro Seite | Waagen | Stufe nach Abschnitt 8 |
  |---|---|---|---|
  | `leicht` | 1 | 3 (mit zwei geht es nach Satz 3 nicht) | 1–2 |
  | `mittel` | bis 2 | 2 oder 3 | 1–2 |
  | `schwer` | bis 3 | 2 oder 3 | 3 |
  | `experte` | bis 3 | 3 | 4 |
- **Ausgabe.** Rätsel werden kanonisch gespeichert, also immer mit $a$ als
  Schwerstem. Im Spielmodus werden Namen und Reihenfolge der Waagen zufällig
  gemischt.

## 8. Schwierigkeit: Lösen in Schritten

### 8.1 Warum nicht die Größe der Faktoren

Ein erster Ansatz hat als Schwierigkeit gezählt, wie viele Waagen das
Farkas-Zertifikat aus 3.2 insgesamt addiert. Das misst aber vor allem, wie
hässlich die Brüche werden. Beim Rätsel

$$
2d < 3c, \qquad 3b < c + d, \qquad 2a = 3c
$$

addiert das Zertifikat für $b < a$ insgesamt 22 Waagen. Ein Mensch rechnet
dagegen in Ketten: aus $2a = 3c$ folgt $c < a$, aus $2d < 3c = 2a$ folgt
$d < a$, und aus $3b < c + d < 2a$ folgt $b < a$.

### 8.2 Definition

Ein Mensch leitet nacheinander einfache Vergleiche $u < v$ zwischen zwei
Gegenständen her und benutzt sie in späteren Schritten weiter. Ein
**Schritt** zeigt einen solchen Vergleich aus einigen Waagen und den schon
bekannten Vergleichen. Ob er gelingt, entscheidet Satz 1, angewandt auf diese
Waagen plus die bekannten Vergleiche als zusätzliche Waagen.

Die **Stufe** eines Rätsels ist:

| Stufe | Name | Bedingung |
|---|---|---|
| 1 | ablesen | Jeder Vergleich $x < a$ folgt aus einer einzigen Waage. |
| 2 | Kette | Alle $x < a$ lassen sich in Schritten zeigen, die je höchstens eine Waage benutzen (plus bekannte Vergleiche). |
| 3 | kombinieren | Dafür braucht mindestens ein Schritt zwei Waagen gleichzeitig. |
| 4 | auflösen | Selbst das reicht nicht; man muss alle drei Waagen zugleich verrechnen, also das Gleichungssystem lösen. |

Stufe 4 kann es nur bei drei Waagen geben. Rätsel mit einem Gegenstand pro
Seite sind nach Satz 3 immer Stufe 1 oder 2.

Beispiel für Stufe 4:

$$
c + 2d < 2a + b, \qquad b + 2d = 3c, \qquad a + b + c = 3d .
$$

Aus keiner Waage und keinem Paar von Waagen folgt ein einfacher Vergleich.
Man muss auflösen: $b = 3c - 2d$, dann $a = 5d - 4c$, eingesetzt in die erste
Waage $6c < 6d$. Daraus folgen $c < d < a$ und $b < c$.

### 8.3 Berechnung

`solve` sammelt die Vergleiche, die in einer Lösung gelten, als Kandidaten und
leitet sie in Schritten ab, bis nichts Neues mehr folgt. Kleine Schritte
kommen zuerst: wenige Waagen, und bei gleich vielen Waagen zuerst ohne
bekannte Vergleiche. Erst wenn das mit einer Waage pro Schritt nicht alle
$x < a$ liefert, sind zwei Waagen pro Schritt erlaubt. Für jeden benötigten
Schritt erzeugt `derive` den Text wie in 3.2; bekannte Vergleiche erscheinen
dort als „bekannt: c < a“. Diese Schritte sind zugleich die Hinweise im
Spielmodus.

Die Stufe ist exakt im Sinne der Definition. Die Reihenfolge der Schritte und
damit der Lösungsweg ist eine Heuristik und nicht immer der kürzeste.

## 9. Der Katalog aller Rätsel

### 9.1 Anzahl

Nach den Festlegungen aus Abschnitt 1 gibt es genau **147 462** verschiedene
Rätsel. Ohne vervielfachte Waagen wie $2c < 2a$ sind es 115 775.

| Stufe | 2 Waagen | 3 Waagen | zusammen | davon ohne Vielfache |
|---|---:|---:|---:|---:|
| 1 ablesen | 69 | 429 | 498 | 325 |
| 2 Kette | 420 | 54 120 | 54 540 | 35 968 |
| 3 kombinieren | 180 | 73 012 | 73 192 | 62 065 |
| 4 auflösen | – | 19 232 | 19 232 | 17 417 |
| **zusammen** | **669** | **146 793** | **147 462** | **115 775** |

`python katalog.py` zählt alle auf und schreibt sie mit ihrer Stufe nach
`data/katalog.json.gz`. Das dauert auf vier Kernen etwa drei Minuten; die Datei ist 450 KB groß.

### 9.2 Aufzählung

1. Von den 603 möglichen Waagen sind 481 damit verträglich, dass $a$ am
   schwersten ist. Zwei davon, $b + c + d < a$ und $b + c + d = a$, bestimmen
   den Schwersten schon allein; sie können in keinem Rätsel vorkommen, weil
   jede weitere Waage überflüssig wäre.
2. **Vorfilter mit Stichproben.** Für jede Waage wird als Bitmaske
   gespeichert, welche der Gewichte $(w_a, w_b, w_c, w_d) \in \{1,\dots,9\}^4$
   sie erfüllen, ergänzt um Gegenbeispiele, die unterwegs anfallen. Erfüllt
   eine Stichprobe alle Waagen eines Systems, aber $a$ ist dort nicht echt am
   schwersten, ist das System sicher kein Rätsel. Dieser Test kann nur
   verwerfen, nie fälschlich annehmen.
3. **Exakt.** Was den Vorfilter übersteht, prüft der Strahlen-Löser
   (Abschnitt 11) nach Satz 1. Für Tripel
   werden nur Systeme betrachtet, in denen kein Paar den Schwersten schon
   bestimmt (Minimalität).
4. **Gleichheit.** Jedes Rätsel wird nach Abschnitt 4.1 kanonisch geschrieben,
   Doppelte fallen weg.
5. **Stufe.** Für jedes Rätsel wird die Stufe aus Abschnitt 8 berechnet.

Gegenproben in den Tests: Stichproben aus dem Katalog bestehen alle Prüfungen
aus den Abschnitten 3, 4 und 8, und jedes Rätsel aus beiden Generatoren steht
mit derselben Stufe im Katalog.

### 9.3 Nutzung

`CatalogSource` filtert den Katalog nach den Einstellungen einer Spielstufe
und zieht ohne Wiederholung. Weil jedes Rätsel gleich wahrscheinlich ist,
spiegelt das Spiel genau die Verteilung aller Rätsel wider. Beispielgewichte
werden als kleinste ganzzahlige Lösung berechnet.

## 10. Der Baukasten

### 10.1 Bausteinregel

Statt Waagen blind zu ziehen, kann man ein Rätsel nach einem Lösungsplan
bauen. Grundlage ist eine Regel, die nachbildet, wie ein Mensch aus einer
Waage und schon bekannten Vergleichen schließt:

> Links stehen $n$ Gegenstände, die alle mindestens so schwer sind wie $x$
> (alles andere links fällt weg). Rechts stehen $m$ Einheiten, die alle
> höchstens so schwer sind wie $h$. Ist $n \ge m$, dann gilt $x < h$.

Denn $n \cdot x \le$ (linke Seite) $<$ (rechte Seite) $\le m \cdot h \le n \cdot h$.
Bei einem Gleichgewicht braucht man zusätzlich etwas Echtes: einen
weggelassenen Gegenstand, $n > m$ oder einen echten Vergleich.

Eine **Einheit** ist ein einzelner Gegenstand oder ein **Block**: eine Summe
wie $c + d$, für die eine Waage $c + d < a$ oder $c + d = a$ zeigt.

| Stufe | Bausteinregel mit ... | Beispiel |
|---|---|---|
| 1 | nur der Waage selbst, rechts nur $a$ | $b + c < a$, $d < a$ |
| 2 | bekannten Vergleichen | $b + c < a$, $2d < a + c$ |
| 3 | bekannten Vergleichen und Blöcken | $c + d < a$, $2b < a + c + d$ |

Im dritten Beispiel helfen die Einzelvergleiche $c < a$ und $d < a$ nicht,
denn daraus folgt nur $2b < 3a$. Erst der Block $c + d$ als Ganzes gibt
$2b < (c + d) + a < 2a$.

Stufe 4 lässt sich so nicht gezielt bauen: Dort folgt aus keiner Waage und
keinem Paar von Waagen ein einfacher Vergleich. Solche Rätsel kommen aus dem
Katalog.

### 10.2 Konstruktion

1. Ziehe Gewichte mit $a$ als echtem Maximum und eine Zielstufe.
2. Wähle nacheinander wahre Waagen, die nach der Bausteinregel der Zielstufe
   etwas Neues zeigen. Bevorzugt werden Waagen, die einen Vergleich mit $a$
   liefern oder die die nächstleichtere Regel nicht schafft.
3. Sobald $b, c, d < a$ feststehen, ist der Plan fertig. Ist das Rätsel schon
   mit der leichteren Regel lösbar, wird es verworfen.
4. Danach exakt prüfen: $a$ eindeutig am schwersten (Satz 1), keine Waage
   überflüssig (4.2), Stufe stimmt (Abschnitt 8), noch nicht vorgekommen
   (4.1).

Die Bausteinregel ist korrekt, aber nicht vollständig: Was sie folgert, gilt
immer (das prüfen die Tests gegen Satz 1), aber nicht alles, was gilt, findet
sie. Deshalb entscheidet am Ende immer die exakte Prüfung.

Gemessen gegen den Zufallsgenerator, bei acht Rätseln je Einstellung (mit dem
Strahlen-Löser aus Abschnitt 11):

| Einstellung | Zufall | Baukasten |
|---|---|---|
| nur Stufe 1 | 8 in 16 s (6402 Versuche) | 8 in 0,6 s (25 Versuche) |
| nur Stufe 2 | 8 in 2,5 s (1122 Versuche) | 8 in 1,2 s (49 Versuche) |
| `mittel` | 8 in 0,5 s (495 Versuche) | 8 in 0,7 s (33 Versuche) |
| `schwer` | 8 in 1,1 s (468 Versuche) | 8 in 3,9 s (161 Versuche) |

Der Baukasten lohnt sich also, wenn eine seltene Stufe verlangt ist, vor allem
Stufe 1. Seit der Strahlen-Löser die exakte Prüfung billig gemacht hat, ist
sonst der Zufall schneller: Er probiert viel mehr, aber jeder Versuch kostet
fast nichts, während der Baukasten seine Bausteinregel in Python auswertet.

## 11. Der Strahlen-Löser

### 11.1 Idee

Die Lösungen eines Systems bilden die Menge

$$
C = \{ w : w_v > 0,\ z \cdot w < 0 	ext{ (geneigte Waagen)},\ y \cdot w = 0 	ext{ (Gleichgewichte)} \}.
$$

Ersetzt man jedes $<$ durch $\le$, erhält man einen spitzen Kegel $K$ im
$\mathbb R^4$. Er wird von wenigen **Kantenstrahlen** $r_1, \dots, r_k$
aufgespannt, bei den Rätseln hier meist vier bis acht.

**Satz 4.** Ist $C$ nicht leer, dann ist $C$ das relative Innere von $K$,
also genau die Menge der Summen $\sum \lambda_i r_i$ mit allen
$\lambda_i > 0$. Daraus folgt:

1. $C$ ist genau dann nicht leer, wenn jede echte Ungleichung (jede geneigte
   Waage und jedes $w_v > 0$) auf mindestens einem Strahl echt erfüllt ist.
2. Aus dem System folgt $x < h$ genau dann, wenn auf allen Strahlen
   $r_x \le r_h$ gilt und auf mindestens einem $r_x < r_h$.

*Beweis.* Eine lineare Funktion $f$ ist auf allen Summen
$\sum \lambda_i r_i$ mit $\lambda_i > 0$ genau dann negativ, wenn
$f(r_i) \le 0$ für alle $i$ und $f(r_i) < 0$ für ein $i$. Für (1) ist
die Summe aller Strahlen dann ein Punkt, der alle echten Ungleichungen echt
erfüllt; umgekehrt liegt jeder Punkt von $C$ in $K$. Für (2) wende man das
auf $f = w_x - w_h$ an. $\square$

Jede Frage nach Satz 1 wird damit zu einer Vorzeichenprüfung an wenigen
ganzzahligen Vektoren. Die Summe aller Strahlen ist zugleich eine
ganzzahlige Lösung.

### 11.2 Berechnung der Strahlen

Double-Description-Methode, ganz in ganzen Zahlen:

1. Beginne mit dem Kegel $w \ge 0$, Strahlen $e_a, e_b, e_c, e_d$.
2. Schneide nacheinander mit jeder Bedingung $z \cdot w \le 0$ (bzw. $= 0$):
   Strahlen mit $z \cdot r \le 0$ (bzw. $= 0$) bleiben. Für jedes Paar aus
   einem Strahl $p$ mit $z \cdot p > 0$ und einem Strahl $n$ mit
   $z \cdot n < 0$ entsteht der Kandidat
   $(z \cdot p)\, n - (z \cdot n)\, p$, der auf der Ebene $z \cdot w = 0$
   liegt.
3. Ein Kandidat ist genau dann ein Kantenstrahl, wenn die an ihm scharfen
   Bedingungen den Rang 3 haben. Nur solche werden behalten.

Die Kegel werden zwischengespeichert. Wer Bedingungen nacheinander anhängt,
wie die Stufenberechnung mit neu gefolgerten Vergleichen, bekommt jeden Kegel
aus dem vorigen und rechnet nur den letzten Schnitt neu.

### 11.3 Messung

Gemessen an zufälligen Rätseln aus dem Katalog:

| Aufgabe | vorher | Strahlen-Löser | Faktor |
|---|---:|---:|---:|
| alle 12 Fragen „folgt $x < h$?“ | 67 ms (Stichproben + Z3) | 0,56 ms | 120 |
| dasselbe nur mit Z3 | 61 ms | 0,56 ms | 108 |
| Stufe berechnen (Abschnitt 8) | 17 ms (Stichproben + Z3) | 2,8 ms | 6 |
| Schwerster und Minimalität | – | 0,4 ms | – |

Der ganze Katalog (Abschnitt 9) entsteht damit in gut 3 statt 46 Minuten, mit genau demselben Inhalt.

Gegenproben in den Tests: Auf zufälligen Systemen aus allen 603 Waagen, auch
mit zusätzlichen bekannten Vergleichen, stimmen Lösbarkeit und alle
Folgerungen mit Z3 überein. Bei der Entwicklung waren es über 14 000
Systeme und 38 000 erzwungene Vergleiche ohne eine Abweichung.

## 12. Das Spiel mit Fenster

```bash
python spiel.py                 # Menü; Schwierigkeit und Zeit dort wählbar
python spiel.py --zeit 45       # eigene Spielzeit in Sekunden
python spiel.py --zeit 0        # Üben ohne Uhr
python spiel.py --stufe Profi
```

Vier Figuren unterscheiden sich in Farbe *und* Form; sie wechseln von Partie zu
Partie. Die Waagen stehen oben links, Mitte rechts und unten links, die
schwerere Schale hängt unten. Auf einer Schale liegen höchstens zwei Figuren
nebeneinander, eine dritte mittig obendrauf, gleiche nebeneinander.

- **Auf Zeit**: so viele Rätsel wie möglich in $t$ Sekunden. Bei einer falschen
  Antwort leuchtet die richtige Figur eine Sekunde lang auf, auch auf den Waagen.
  Am Ende stehen gespielte Runden, richtige, falsche und die Punkte da. Je
  Schwierigkeit und Zeit wird ein Rekord gespeichert (`~/.waagenspiel/bestenliste.json`).
- **Üben**: ohne Uhr. Eine Leiste rechts zeigt auf Wunsch die Lösungsschritte
  (Abschnitt 8). Nach einer falschen Antwort erklärt sie, warum die gewählte
  Figur leichter ist als die richtige. Das ist der Farkas-Beweis aus Abschnitt 3,
  mit den Namen der Figuren.
- **Schwierigkeit**: Leicht, Mittel, Schwer und Profi entsprechen den Stufen 1–4.
  „Steigend“ beginnt bei 1. Drei Richtige in Folge heben die Stufe, ein Fehler
  senkt sie.

Alle Rätsel kommen aus dem Katalog (ohne Vielfache wie `2b < 2a`). Für jede
Runde werden die Figuren zufällig umbenannt, die Waagen gemischt und
manche gespiegelt.

| Teil | Datei |
|---|---|
| Spiellogik ohne Oberfläche: Runden, Partie, Punkte, Stufen, Bestenliste | `src/waagenspiel/game.py` |
| Oberfläche (tkinter); bekommt die Partie von außen | `src/waagenspiel/gui.py` |
| Start | `spiel.py` |
| Tests der Spiellogik | `tests/test_game.py` |

### 12.1 Was am alten Spiel (`game_of_scales/`, inzwischen gelöscht) falsch war

Alle 3 756 gespeicherten Rätsel wurden mit dem Strahlen-Löser nachgerechnet.
**28 haben keinen eindeutig Schwersten**, zum Beispiel
`2c < d`, `2d < a`, `b < 2a` mit der Antwort a. Mit
$(a, b, c, d) = (10, 15, 1, 4)$ ist aber b am schwersten. Dazu kommen 983
doppelte Rätsel und 377 mit einer Waage, die nach dem Kürzen nichts aussagt
(etwa `b < c + d + b`).

Die Fehler im Prüfcode:

1. Geneigte Waagen wurden in Paare zerlegt: Aus `b < a + a` wurde `b < a`, aus
   `a + b = c + d` wurden `a = c`, `a = d`, `b = c` und `b = d`. Das ist falsch,
   sobald auf einer Seite mehrere Gegenstände liegen.
2. Gekürzt wurde mit Mengen statt Anzahlen: Aus `a + a + b` gegen `a + c` wurde
   `b` gegen `c` statt `a + b` gegen `c`.
3. Rangplätze 0, 1, 2, … wurden als Gewichte eingesetzt. Ob eine Reihenfolge
   möglich ist, hängt aber von den echten Gewichten ab, und 0 ist kein
   erlaubtes Gewicht.
4. Am Ende entschied eine Zufallsstichprobe. Sie kann Gegenbeispiele finden,
   aber Eindeutigkeit nie beweisen. Umgekehrt verwirft sie richtige Rätsel mit
   Gleichgewichten wie `2a = b + c`, weil Zufallsgewichte sie fast nie genau
   treffen.

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

Die Relationen haben das JSON-Format
`{"left": {"b": 1, "c": 1}, "operator": "<", "right": {"a": 1}}`.
