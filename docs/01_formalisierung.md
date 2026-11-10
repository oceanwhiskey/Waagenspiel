# Mathematische Formalisierung

## 1. Zweck und Modellierungsentscheidungen

Die Buchstaben \(a,b,c,d\) bezeichnen im Folgenden **Symbole für vier
Gewichte**, nicht bereits fest vorgegebene Zahlen. Eine Lösung eines
Relationssystems ist eine zulässige Belegung dieser Symbole mit Zahlen.

Die folgende Formalisierung trifft vier für die weitere Implementierung
verbindliche Entscheidungen:

1. \(\mathbb N_{>0}=\{1,2,3,\ldots\}\), und die vier Gewichte müssen
   paarweise verschieden sein.
2. Algebraisch gleiche Einzelrelationen werden durch eine primitive
   Normalform identifiziert. Insbesondere sind \(2a<2b\) und \(a<b\)
   dieselbe Relation.
3. Zwei Systeme gelten genau dann als gleich, wenn ihre **Lösungsmengen**
   durch eine gemeinsame Umbenennung der vier Symbole ineinander
   übergehen. Dadurch werden auch verschiedene Relationsbasen mit exakt
   demselben Informationsgehalt identifiziert. Die bloß strukturelle
   Übereinstimmung der Relationen bleibt ein schneller Vorfilter.
4. „Keine Information verlieren“ wird streng modelltheoretisch verstanden:
   Das Entfernen jeder einzelnen Relation muss die Menge zulässiger
   Lösungen echt vergrößern.

Die Gründe sowie denkbare, aber nicht gewählte Alternativen stehen in
Abschnitt 10.

## 2. Gewichte, Seiten und Relationen

Sei

\[
V=\{a,b,c,d\}.
\]

Eine Seite einer Relation ist ein Multivektor

\[
m\colon V\longrightarrow \mathbb N_0.
\]

Dabei ist \(m(x)\) die Häufigkeit des Symbols \(x\) auf dieser Seite. Ihre
Größe und ihr Träger sind

\[
\lVert m\rVert_1=\sum_{x\in V}m(x),
\qquad
\operatorname{supp}(m)=\{x\in V:m(x)>0\}.
\]

Eine zulässige Seite erfüllt

\[
1\leq \lVert m\rVert_1\leq 3.
\]

Eine rohe Relation ist ein Tripel

\[
r=(m_L,\mathbin\triangleleft,m_R),
\qquad \mathbin\triangleleft\in\{=,<\},
\]

mit zwei zulässigen Seiten. Die Forderung, dass kein Symbol auf beiden
Seiten steht, lautet

\[
\operatorname{supp}(m_L)\cap\operatorname{supp}(m_R)=\varnothing.
\]

Die Zahl „drei“ zählt also Vorkommen mit Multiplizität: \(2a+b\) hat
Seitengröße drei.

## 3. Normalform einer Einzelrelation

Zu \(r\) gehört der vorzeichenbehaftete Koeffizientenvektor

\[
z(r)=m_L-m_R\in\mathbb Z^V.
\]

Für eine Gleichung bedeutet die Relation \(z\cdot w=0\), für eine
Kleiner-Relation bedeutet sie \(z\cdot w<0\). Damit erhält man folgende
Normalform.

1. Falls Eingaben mit demselben Symbol auf beiden Seiten zugelassen werden,
   werden zunächst die gemeinsamen Anteile komponentenweise gekürzt. Für
   die Erzeugung werden solche Eingaben gar nicht erst erzeugt.
2. Ist nach dem Kürzen eine Seite leer, wird die Relation verworfen. Damit
   bleibt die README-Forderung „auf beiden Seiten mindestens ein Element“
   erhalten.
3. Man teile \(z\) durch

   \[
   g=\gcd\{|z_x|:z_x\neq 0\}.
   \]

   Der resultierende Vektor ist primitiv.
4. Bei einer Gleichung beschreiben \(z\) und \(-z\) dieselbe Relation. Für
   die eindeutige Darstellung wird das Vorzeichen so gewählt, dass der
   erste von null verschiedene Eintrag in der Reihenfolge \(a,b,c,d\)
   positiv ist.
5. Bei \(<\) darf das Vorzeichen **nicht** gewechselt werden, denn
   \(z\cdot w<0\) und \((-z)\cdot w<0\) sind entgegengesetzte Aussagen.
   Eine etwaige Eingabe mit \(>\) wird zuerst durch Vertauschen der Seiten
   in eine \(<\)-Relation überführt.

Nach der Normierung werden die beiden Seiten durch den positiven und den
negativen Anteil von \(z\) rekonstruiert. Beide müssen weiterhin Größen
zwischen eins und drei haben. Eine normalisierte Relation kann somit
eindeutig als

\[
(\operatorname{op},z_a,z_b,z_c,z_d),
\qquad \operatorname{op}\in\{\texttt{eq},\texttt{lt}\},
\]

gespeichert werden.

Beispiele:

\[
2a<2b\ \longmapsto\ a<b,
\qquad
b=a+c\ \longmapsto\ a-b+c=0.
\]

Dagegen sind \(a<b\) und \(b<a\) verschiedene Relationen.

## 4. Relationssysteme

Sei \(\mathcal R\) die endliche Menge aller nach Abschnitt 3 zulässigen
normalisierten Relationen. Ein Relationssystem ist eine **Menge**

\[
R\subseteq\mathcal R,
\qquad |R|\in\{2,3\}.
\]

Folglich gilt:

- Die Reihenfolge der Relationen ist bedeutungslos.
- Dieselbe normalisierte Relation kann nicht zweimal vorkommen.
- Zwei syntaktisch verschiedene rohe Relationen, die dieselbe Normalform
  haben, erhöhen die Größe des Systems nicht.

Für eine deterministische Darstellung werden Relationen zunächst nach
\(\operatorname{op}\) und danach lexikographisch nach
\((z_a,z_b,z_c,z_d)\) sortiert. Welche der beiden Operationen zuerst kommt,
ist beliebig, muss aber in Programm und JSON einheitlich festgelegt werden.

## 5. Semantik über positiven, verschiedenen natürlichen Gewichten

Der gemeinsame Hintergrundbereich aller Systeme ist

\[
D=\left\{
w\in\mathbb Z_{>0}^{V}:
w_x\neq w_y\text{ für alle }x\neq y
\right\}.
\]

Für eine Seite \(m\) ist

\[
\llbracket m\rrbracket_w=\sum_{x\in V}m(x)w_x.
\]

Die Erfüllungsrelation ist

\[
\begin{aligned}
w\models(m_L=m_R)
&\iff \llbracket m_L\rrbracket_w=\llbracket m_R\rrbracket_w,\\
w\models(m_L<m_R)
&\iff \llbracket m_L\rrbracket_w<\llbracket m_R\rrbracket_w.
\end{aligned}
\]

Die Modellmenge eines Systems ist

\[
\operatorname{Mod}(R)
=\{w\in D:\forall r\in R\colon w\models r\}.
\]

Ein System ist erfüllbar, wenn \(\operatorname{Mod}(R)\neq\varnothing\).
Für eine Aussage \(\varphi\) schreiben wir

\[
R\models_D\varphi
\iff
\forall w\in\operatorname{Mod}(R)\colon w\models\varphi.
\]

Erfüllbarkeit muss immer separat geprüft werden, damit aus einem
widersprüchlichen System nicht vakuos jede Aussage „folgt“.

### Nützliche Exaktheitsaussage

Alle vorkommenden Relationen sind homogen und haben ganzzahlige
Koeffizienten. Nach Aufspaltung der Paarverschiedenheit in eine der 24
möglichen strengen Reihenfolgen gilt daher:

> Ein Zweig besitzt genau dann eine positiv-ganzzahlige Lösung, wenn er
> eine reelle Lösung besitzt.

Die nichttriviale Richtung folgt daraus, dass eine nichtleere, durch
rationale Gleichungen und strenge rationale Ungleichungen beschriebene
Menge einen rationalen Punkt enthält. Multiplikation mit einem gemeinsamen
Nenner liefert dann eine ganzzahlige Lösung. Dadurch sind exakte lineare
Machbarkeitstests möglich; eine willkürliche obere Schranke für die
Gewichte gehört **nicht** zur Definition.

## 6. Eindeutig bestimmtes schwerstes Element

Da jede zulässige Belegung paarweise verschiedene Werte besitzt, hat jede
einzelne Belegung ein eindeutiges Maximum. Gefordert ist mehr: Dessen
**Name** muss in allen Modellen derselbe sein.

Ein Symbol \(x\in V\) heißt durch \(R\) als schwerstes Element erzwungen,
wenn

\[
\operatorname{Mod}(R)\neq\varnothing
\quad\text{und}\quad
\forall w\in\operatorname{Mod}(R)\ \forall y\in V\setminus\{x\}:
w_x>w_y.
\]

Bei einem erfüllbaren System können nicht zwei verschiedene Symbole diese
Eigenschaft haben. Die README-Konvention verlangt nach einer passenden
Umbenennung, dass das erzwungene Symbol \(a\) ist.

Für die Implementierung ist dies äquivalent zu

\[
\begin{aligned}
&\operatorname{Mod}(R)\neq\varnothing,\\
&\operatorname{Mod}(R)\cap\{w:w_a<w_x\}=\varnothing
\quad\text{für }x\in\{b,c,d\}.
\end{aligned}
\]

Wegen der Paarverschiedenheit ist \(w_a\not>w_x\) genau \(w_a<w_x\).

### Warum keine eindeutige Zahlenbelegung gemeint sein kann

Ist \(w\in\operatorname{Mod}(R)\), dann ist wegen der Homogenität auch
\(kw\in\operatorname{Mod}(R)\) für jedes \(k\in\mathbb N_{>0}\). Bereits
\(w\) und \(2w\) sind verschiedene Belegungen. Kein erfüllbares System der
gegebenen Art besitzt daher eine eindeutige numerische Lösung. Der Ausdruck
„eindeutige Lösung“ im Problemteil muss, sofern keine zusätzliche
Normierung der Zahlen vorgegeben wird, als „eindeutig bestimmtes
schwerstes Element“ gelesen werden.

## 7. Semantische Gleichheit modulo Umbenennung

Eine Umbenennung ist eine Permutation \(\pi\in\operatorname{Sym}(V)\). Sie
wirkt auf einen Koeffizientenvektor durch

\[
(\pi z)_{\pi(x)}=z_x
\]

und komponentenweise auf allen Relationen eines Systems. Nach jeder
Umbenennung wird wieder die Normalform aus Abschnitt 3 gebildet. Es wird
stets **dieselbe** Permutation auf alle Relationen eines Systems angewendet.

### Strukturelle Isomorphie als Vorfilter

Zwei Systeme \(R,T\) heißen strukturell isomorph, geschrieben

\[
R\cong T,
\]

wenn

\[
\exists\pi\in\operatorname{Sym}(V):
T=\operatorname{NF}(\pi R)
\]

als Mengen normalisierter Relationen gilt. Einen strukturellen Schlüssel
erhält man, indem man die sortierten Relationskodes
\((\operatorname{op},z_a,z_b,z_c,z_d)\) für alle 24 Permutationen bildet
und das lexikographisch kleinste Tupel wählt.

Strukturelle Isomorphie impliziert die nachfolgend definierte semantische
Äquivalenz. Deshalb darf die Implementierung zuerst je struktureller Klasse
nur einen Kandidaten behalten und erst danach die teureren semantischen
Schlüssel berechnen. Die Umkehrung gilt nicht; ein verschiedener
struktureller Schlüssel ist also **kein** Beweis semantischer
Verschiedenheit.

### Hauptbegriff: gleiche Lösungsmengen

Zwei Systeme sind semantisch äquivalent modulo Umbenennung, geschrieben

\[
R\equiv_{\mathrm{sem}}T,
\]

wenn

\[
\exists\pi\in\operatorname{Sym}(V):
\operatorname{Mod}(T)
=\operatorname{Mod}(\operatorname{NF}(\pi R)).
\]

Diese Definition identifiziert genau Systeme mit demselben vollständigen
Informationsgehalt; sie ist der Gleichheitsbegriff für \(\mathcal S\).

Ein kurzes Beispiel zweier verschiedener Basen ist

\[
\begin{aligned}
R&=\{a=b+c,\ b=c+d\},\\
T&=\{a=b+c,\ a=2c+d\}.
\end{aligned}
\]

Aus den beiden Gleichungen von \(R\) folgt \(a=2c+d\). Umgekehrt folgt
aus den beiden Gleichungen von \(T\) durch Subtraktion \(b=c+d\). Daher
gilt \(\operatorname{Mod}(R)=\operatorname{Mod}(T)\). Beide Systeme sind
erfüllbar, zum Beispiel durch \((a,b,c,d)=(4,3,1,2)\), und erzwingen \(a\)
als Maximum. Beide Basen sind außerdem streng irredundant. Sie sind aber
nicht strukturell isomorph, weil nur \(T\) eine Relation mit einem
Koeffizienten \(2\) enthält.

### Exakter Closure-Schlüssel über alle 567 Atome

Die Menge \(\mathcal R\) der normalisierten Einzelrelationen aus Abschnitt
4 enthält genau 567 Atome. Um diese Zahl nachzuvollziehen, betrachte alle
primitiven Vektoren \(z\in\mathbb Z^4\) mit

\[
1\leq\lVert z^+\rVert_1\leq3,
\qquad
1\leq\lVert z^-\rVert_1\leq3,
\qquad
\gcd(|z_x|:z_x\neq0)=1.
\]

Nach den beiden Seitensummen verteilen sich die **gerichteten** Vektoren
wie folgt:

| \(\lVert z^+\rVert_1\backslash\lVert z^-\rVert_1\) | 1 | 2 | 3 |
|---:|---:|---:|---:|
| 1 | 12 | 24 | 40 |
| 2 | 24 | 30 | 64 |
| 3 | 40 | 64 | 80 |

Ihre Summe ist 378. Jeder gerichtete Vektor liefert ein \(<\)-Atom. Bei
Gleichungen werden \(z\) und \(-z\) identifiziert, also gibt es
\(378/2=189\) Gleichungsatome. Insgesamt ist damit

\[
|\mathcal R|=378+189=567.
\]

Fixiere einmalig die deterministische Reihenfolge

\[
\mathcal R=(q_1,\ldots,q_{567})
\]

nach dem Relationskode aus Abschnitt 4. Der semantische Abschluss eines
Systems innerhalb dieses vollständigen Atomraums ist

\[
\operatorname{Cl}(R)
=\{q\in\mathcal R:R\models_D q\}.
\]

Sein Closure-Schlüssel ist der Bitvektor

\[
C(R)\in\{0,1\}^{567},
\qquad
C(R)_i=1\iff R\models_D q_i.
\]

Dieser endliche Schlüssel ist für die hier betrachteten Systeme exakt:

\[
\operatorname{Mod}(R)=\operatorname{Mod}(T)
\iff C(R)=C(T).
\]

Die Hinrichtung ist unmittelbar. Für die Rückrichtung gilt
\(R\subseteq\operatorname{Cl}(R)=\operatorname{Cl}(T)\); also impliziert
\(T\) jede Relation aus \(R\) und
\(\operatorname{Mod}(T)\subseteq\operatorname{Mod}(R)\). Vertauschen von
\(R,T\) liefert die andere Inklusion. Entscheidend ist, dass \(R\) und
\(T\) selbst ausschließlich aus Atomen von \(\mathcal R\) bestehen.

Der kanonische semantische Schlüssel modulo Umbenennung ist

\[
\operatorname{semkey}(R)
=\min_{\pi\in\operatorname{Sym}(V)}
C(\operatorname{NF}(\pi R)),
\]

wobei das Minimum lexikographisch über Bitvektoren genommen wird. Dann
gilt exakt

\[
R\equiv_{\mathrm{sem}}T
\iff
\operatorname{semkey}(R)=\operatorname{semkey}(T).
\]

Die 24 Closure-Vektoren müssen nicht jeweils neu durch 567 Solveraufrufe
bestimmt werden. Folgerbarkeit ist umbenennungsinvariant, also

\[
\operatorname{Cl}(\operatorname{NF}(\pi R))
=\operatorname{NF}(\pi\operatorname{Cl}(R)).
\]

Nach einmaliger Vorberechnung der von jeder \(\pi\) induzierten Permutation
der 567 Bitpositionen genügt daher ein einziger Closure-Vektor \(C(R)\);
die übrigen entstehen durch reine Bitpermutation.

Sind beide Systeme bereits so beschriftet, dass \(a\) das erzwungene
Maximum ist, genügen die sechs Permutationen von \(b,c,d\): Jede
semantische Umbenennung muss das eindeutig ausgezeichnete Symbol \(a\)
festlassen.

Für jedes Closure-Atom wird eine Folgerungsprüfung benötigt. Diese ist als
Gegenmodelltest implementierbar:

\[
R\models_D q
\iff
\operatorname{Mod}(R\cup\{\neg q\})=\varnothing,
\]

wobei \(\neg(L<R)\) als \(L\geq R\) und \(\neg(L=R)\) als die zwei Fälle
\(L<R\) oder \(R<L\) behandelt wird. Closure-Schlüssel sollten
zwischengespeichert werden.

### Implementierte äquivalente Kegel-Signatur

Der Closure-Schlüssel bleibt die Referenzdefinition der semantischen
Äquivalenz. Für die Massenerzeugung wird dieselbe Semantik kompakter durch
eine exakte Kegel-Signatur berechnet. Sei

\[
E_R=\operatorname{span}_{\mathbb Q}
\{z(r):r\in R,\ \operatorname{op}(r)=\texttt{eq}\},
\qquad
L_R=E_R^\perp.
\]

Der Gleichungsanteil der Signatur ist die eindeutige rationale RREF einer
Matrix mit Zeilenraum \(E_R\). Wähle daraus deterministisch eine rationale
Basismatrix \(B_R\) von \(L_R\), sodass \(w=B_Ry\). Zu den strikten
Ungleichungsnormalen gehören

\[
A_R=\{z(r):\operatorname{op}(r)=\texttt{lt}\}
\cup\{-e_a,-e_b,-e_c,-e_d\};
\]

die vier letzten Zeilen kodieren \(w_x>0\) als \(-e_x\cdot w<0\). Nach
Einschränkung auf den Lösungsraum \(L_R\) der Gleichungen erhält man den
dualen Normalenkegel

\[
K_R^\vee
=\operatorname{cone}_{\geq0}
\{\alpha B_R:\alpha\in A_R\}.
\]

Die implementierte Signatur ist

\[
\Theta(R)=
\left(
\operatorname{RREF}_{\mathbb Q}(E_R),
\operatorname{sort}\left(\operatorname{ExtRays}(K_R^\vee)\right)
\right),
\]

wobei jeder Extremstrahl durch seinen primitiven ganzzahligen Generator
mit positiver Skalierungsrichtung dargestellt wird. Nicht-extreme
Ungleichungsnormalen sind nicht gespeichert, weil sie nichtnegative
Linearkombinationen der Extremstrahlen sind.

Warum ist dies exakt? Ohne `Distinct` ist die reelle strikte Lösungsmenge

\[
O_R=\{w\in L_R:\alpha\cdot w<0\text{ für alle }\alpha\in A_R\}.
\]

Ist sie nichtleer, dann ist

\[
O_R=\operatorname{relint}_{L_R}(K_R),
\qquad
\overline{O_R}^{\,L_R}=K_R,
\qquad
K_R=\{w\in L_R:\alpha\cdot w\leq0\ (\alpha\in A_R)\}.
\]

Strikte Erfüllbarkeit macht \(K_R^\vee\) spitz; daher bestimmen seine
Extremstrahlen den ganzen dualen Kegel und durch Polarität den
abgeschlossenen primären Kegel \(K_R\). Umgekehrt gewinnt man aus \(K_R\)
seinen relativen Innenraum \(O_R\). Somit bestimmen RREF und Extremstrahlen
genau dieselbe Modelltheorie wie der Closure-Schlüssel.

Die Paarverschiedenheit ändert diesen Schlüssel nicht. Setze

\[
O_R^{\neq}=O_R\setminus
\bigcup_{x\neq y}\{w:w_x=w_y\}.
\]

Ist \(O_R^{\neq}\neq\varnothing\), so ist keine der endlich vielen
Gleichheitshyperebenen identisch mit \(L_R\); ihr Komplement ist deshalb
dicht in \(O_R\). Also gilt

\[
\overline{O_R^{\neq}}^{\,L_R}=K_R.
\]

Da alle Daten rational und homogen sind, liegen rationale
Distinct-Punkte ebenfalls dicht; durch Beseitigen der Nenner entstehen
positive, paarweise verschiedene natürliche Lösungen. Die Kegel-Signatur
ist damit auch für den in Abschnitt 5 festgelegten natürlichen Bereich
exakt: Verschiedene offene Kegel besitzen einen rationalen
Distinct-Gegenpunkt, der zu einem ganzzahligen Gegenmodell skaliert werden
kann. Unter Umbenennungen wird \(\Theta(R)\) wie der Closure-Schlüssel
kanonisiert. Tests können und sollen die kompakte Implementierung gegen die
567-Atom-Closure als Spezifikationsorakel vergleichen.

### Die zusätzliche Reihenfolgekonvention aus Punkt 6 des README

Die Bedingungen

\[
R\not\models_D b>c,
\qquad
R\not\models_D d>c,
\qquad
R\not\models_D d>b
\]

sind allein noch keine eindeutige kanonische Beschriftung. Sie können aber
als zusätzliche Ausgabe-Konvention erfüllt werden. Definiere auf
\(\{b,c,d\}\)

\[
x\succ_R y\iff R\models_D x>y.
\]

Wegen der Erfüllbarkeit ist \(\succ_R\) eine strikte partielle Ordnung.
Jede solche Ordnung besitzt eine lineare Erweiterung. Beschriftet man eine
lineare Erweiterung in der Reihenfolge \(c,b,d\), so treten keine der drei
verbotenen Rückwärtsfolgerungen auf. Gibt es mehrere mögliche
Beschriftungen oder mehrere semantisch äquivalente Relationsbasen, wird
unter ihnen der lexikographisch kleinste Präsentationskode
\((|R|,\operatorname{sortierte\ Relationskodes})\) gewählt. Damit entsteht
genau ein deterministischer Präsentationsrepräsentant jeder semantischen
Äquivalenzklasse.

Die mathematische Gleichheitsprüfung muss den Closure-Schlüssel oder die
bewiesen äquivalente Kegel-Signatur verwenden und darf nicht bloß auf die
drei Folgerungen oder den strukturellen Schlüssel vertrauen.

## 8. Strenge Irredundanz

Eine Relation \(r\in R\) ist redundant bezüglich des festen
Hintergrundbereichs \(D\), wenn

\[
R\setminus\{r\}\models_D r.
\]

Das System heißt **streng irredundant**, wenn keine seiner Relationen
redundant ist. Äquivalent gilt für jede Relation \(r\in R\)

\[
\operatorname{Mod}(R)
\subsetneq
\operatorname{Mod}(R\setminus\{r\}).
\]

Die für einen Solver nützlichste äquivalente Form ist die Existenz eines
Gegenmodells:

\[
\forall r\in R\ \exists w\in D:
\left(
\forall q\in R\setminus\{r\}:w\models q
\right)
\land w\not\models r.
\]

Beim Negieren ist wichtig:

- Die Negation von \(L<R\) ist \(L\geq R\), nicht nur \(L>R\).
- Die Negation von \(L=R\) ist \(L\neq R\), also die Fallunterscheidung
  \(L<R\) oder \(R<L\).

Beispielsweise ist in \(\{a<b,\ b<c,\ a<c\}\) die letzte Relation
redundant, weil sie aus den ersten beiden folgt.

Die Aussage „\(a\) ist das schwerste Element“ ist hierbei ein **Ergebnis**
und kein zusätzliches Hintergrundaxiom. Sie darf beim Redundanztest nicht
vorausgesetzt werden.

### Optional stärkere Zielminimalität

Eine andere mögliche Lesart von „kein Mehrwert“ wäre, dass jede Relation
für das bloße Erkennen des schwersten Elements notwendig sein muss:

\[
\forall r\in R:\quad
R\setminus\{r\}\text{ erzwingt }a\text{ nicht mehr als Maximum}.
\]

Diese **Zielminimalität** ist strenger als die oben definierte
Informations-Irredundanz. Eine Relation kann die Modellmenge echt
verkleinern und damit Information liefern, obwohl \(a\) auch ohne sie
schon als Maximum feststeht. Wegen der Formulierung „keine Information
verliere“ wird für die Hauptdefinition die modelltheoretische, strenge
Irredundanz verwendet. Falls mit „Mehrwert“ ausschließlich der Spielzweck
gemeint war, sollte Zielminimalität als zusätzlicher Filter aktiviert
werden.

## 9. Präzise Definition der gesuchten Menge

Sei \(\mathcal A\) die Menge aller Relationssysteme \(R\subseteq\mathcal R\),
für die gilt:

1. \(|R|\in\{2,3\}\),
2. \(\operatorname{Mod}(R)\neq\varnothing\),
3. genau ein Symbol wird in allen Modellen als Maximum erzwungen,
4. \(R\) ist streng irredundant.

Die abstrakte gesuchte Menge ist die Quotientenmenge

\[
\boxed{
\mathcal S=\mathcal A/\!\equiv_{\mathrm{sem}}
}
\]

unter der semantischen Äquivalenz modulo Umbenennung aus Abschnitt 7. Für
JSON wird aus jeder Klasse genau eine konkrete Relationsbasis als
Präsentationsrepräsentant ausgegeben: Das erzwungene Maximum wird \(a\)
genannt; die restlichen Symbole und gegebenenfalls mehrere äquivalente
Basen werden nach der dort beschriebenen Konvention kanonisiert.

Damit sind die fünf voneinander unabhängigen Prüfungen für einen Kandidaten
klar getrennt:

1. syntaktische Zulässigkeit und Relationsnormalform,
2. Erfüllbarkeit und eindeutig erzwungenes Maximum,
3. strenge Irredundanz durch je ein Gegenmodell,
4. schnelle Vorgruppierung durch den strukturellen Schlüssel,
5. endgültige Deduplizierung durch die kanonische Kegel-Signatur
   (äquivalent zur Closure-Referenz).

## 10. Verbleibende Ambiguitäten und begründete Entscheidungen

### Semantische Gleichheit als Hauptbegriff

Festgelegt ist die vollständige semantische Gleichheit der Lösungsmengen
modulo gemeinsamer Umbenennung. Sie ist gröber als strukturelle Isomorphie:
Verschiedene irredundante Relationsbasen können denselben
Informationsgehalt besitzen. Das vermeidet doppelte Einträge für
äquivalente mathematische Probleme. Die strukturelle Isomorphie bleibt nur
als günstiger positiver Vorfilter und zur Auswahl einer konkreten
Darstellung erhalten; sie entscheidet nicht über die Zugehörigkeit zu
\(\mathcal S\).

### Skalierte Einzelrelationen

Die primitive Normalform behandelt etwa \(a<b\), \(2a<2b\) und
\(3a<3b\) als dieselbe Information. Das ist mathematisch und für eine
kompakte Erzeugung sinnvoll. Soll die Anzahl physisch aufgelegter Exemplare
Teil eines Spielzugs sein, müssten diese Relationen stattdessen syntaktisch
unterschieden werden; dann entfällt Schritt 3 der Relationsnormalform.

### Bedeutung von „eindeutige Lösung“

Ohne eine Zusatzbedingung wie \(\gcd(w_a,w_b,w_c,w_d)=1\), eine feste
Gesamtsumme oder obere Grenzen ist eine eindeutige Zahlenbelegung wegen der
Skalierungsinvarianz unmöglich. Die vorliegende Definition folgt deshalb
der Eigenschaft „eindeutig genau ein Element ... am schwersten“ aus dem
README.

### Bedeutung von „Mehrwert“

Die Hauptdefinition verwendet den exakten Informationsbegriff
\(\operatorname{Mod}(R)\subsetneq
\operatorname{Mod}(R\setminus\{r\})\). Die alternative Zielminimalität ist
in Abschnitt 8 separat angegeben, damit eine spätere fachliche Entscheidung
keine Änderung an den übrigen Definitionen erfordert.
