# Algorithmus zur Erzeugung der Systeme

## 1. Ziel und festgelegte Interpretation

Für eine Belegung schreiben wir

\[
x=(x_a,x_b,x_c,x_d)\in\mathbb N_{>0}^4.
\]

Alle Relationen im Problem sind homogen. Ist $x$ eine Lösung, dann ist daher
auch $m x$ für jedes $m\in\mathbb N_{>0}$ eine Lösung. Eine **numerisch
eindeutige Belegung** kann es folglich nicht geben. Im Folgenden bedeutet
„eindeutige Lösung“ deshalb genau das, was Eigenschaft 5 verlangt: Aus dem
System muss eindeutig folgen, welches der vier Gewichte das schwerste ist.

Da $G=\{a,b,c,d\}$ vier Gewichte als Elemente einer Menge bezeichnet, werden
die vier Werte als paarweise verschieden modelliert. Der gemeinsame
Hintergrund ist also

\[
D(x)=\bigwedge_i x_i>0\ \land\ \operatorname{Distinct}(x_a,x_b,x_c,x_d).
\]

Diese Bedingung gehört zu jeder SAT- und Folgerungsanfrage.

Zwei Systeme gelten hier als gleich, wenn sie dieselbe Information über
positive Gewichte enthalten, gegebenenfalls nach einer Umbenennung der vier
Gewichte. Das ist stärker als bloße Textgleichheit und passt zu Eigenschaft 9.
Die genaue Definition steht in Abschnitt 5.

## 2. Kanonische Darstellung einer Relation

Die Variablenreihenfolge sei stets

\[
(a,b,c,d).
\]

Eine Seite einer Relation wird durch ihren Koeffizientenvektor beschrieben.
Beispielsweise hat $2a+c$ den Vektor $(2,0,1,0)$. Für die linke und rechte
Seite seien dies $l,r\in\mathbb N_0^4$. Zulässig sind genau die Paare mit

\[
1\leq \lVert l\rVert_1\leq 3,\qquad
1\leq \lVert r\rVert_1\leq 3,\qquad
l_i r_i=0\quad\text{für alle }i.
\]

Die letzte Bedingung ist die geforderte Kürzung: Keine Variable kommt auf
beiden Seiten vor. Mit

\[
\delta=l-r
\]

lautet die Relation entweder $\delta\cdot x=0$ oder
$\delta\cdot x<0$.

### 2.1 Primitive Normalform

Sei

\[
g=\gcd\{\lvert\delta_i\rvert:\delta_i\neq0\}.
\]

Man ersetzt $\delta$ durch $\delta/g$. Dies entfernt beispielsweise die
doppelte Schreibweise $2a=2b$ gegenüber $a=b$, ohne die Lösungsmenge zu
ändern. Linke und rechte Seite lassen sich danach eindeutig als positiver und
negativer Anteil von $\delta$ rekonstruieren.

Bei einer Gleichung sind $\delta$ und $-\delta$ dieselbe Relation. Das
Vorzeichen wird so gewählt, dass der erste von null verschiedene Eintrag in
der Reihenfolge $a,b,c,d$ positiv ist. Bei einer Ungleichung darf das
Vorzeichen **nicht** gewechselt werden, denn $\delta\cdot x<0$ und
$-\delta\cdot x<0$ haben entgegengesetzte Bedeutung.

Der kanonische Schlüssel eines Atoms ist somit

```text
(operator, delta[0], delta[1], delta[2], delta[3])
```

mit einer fest dokumentierten Ordnung der Operatoren. Alle Schlüssel werden
sortiert und fortlaufend nummeriert.

### 2.2 Größe des Relationsuniversums

Es gibt 34 mögliche nichtleere Seitenvektoren mit Koeffizientensumme höchstens
3. Von den geordneten, disjunkten Seitenpaaren bleiben nach der primitiven
Normalisierung

- 378 gerichtete `<`-Relationen und
- 189 ungerichtete `=`-Relationen,

also insgesamt

\[
\lvert R\rvert=567
\]

verschiedene atomare Relationen. Diese Zahlen sind zugleich nützliche
Regressionstests für die Implementierung.

## 3. Logische Grundoperationen mit Z3

Für ein System $s\subseteq R$ bezeichnet

\[
F_s(x)=\bigwedge_{r\in s}r(x)
\]

seine Formel und

\[
D(x)=x_a>0\land x_b>0\land x_c>0\land x_d>0
\land\operatorname{Distinct}(x_a,x_b,x_c,x_d)
\]

den Wertebereich.

### 3.1 Exakte reelle Arithmetik für ganzzahlige Gewichte

Der Generator verwendet vier Z3-`Real`-Variablen, die
Positivitätsbedingungen und `Distinct(a,b,c,d)`. Seine Anfragen liegen damit
in quantorenfreier linearer reeller Arithmetik (`QF_LRA`). Das ist hier keine
ungenaue Relaxation, sondern entscheidet auch die ursprüngliche Frage über
positiven ganzen Zahlen exakt.

Die nichttriviale Richtung lautet: Hat eine Generatoranfrage eine reelle
Lösung, dann hat sie auch eine positive ganzzahlige Lösung. Alle vorkommenden
Vergleiche sind homogen und besitzen rationale Koeffizienten. Man wählt in
einem reellen Modell für jede Disequality aus `Distinct` sowie für jede andere
Disjunktion den dort erfüllten Zweig. Es bleibt ein nichtleeres System aus
rationalen linearen Gleichungen sowie strikten oder nichtstrikten rationalen
Ungleichungen. Eine solche rationale Polyederzelle enthält einen rationalen
Punkt; die strikt erfüllten Vergleiche können dabei wegen ihrer Offenheit
beibehalten werden. Multiplikation mit dem Hauptnenner liefert einen positiven
ganzzahligen Punkt. Homogenität erhält Gleichungen, Ungleichungsrichtungen und
Paarverschiedenheit beim Skalieren. Die umgekehrte Richtung ist trivial.

Das Argument gilt auch für Gegenmodelltests: Die Negationen
$L\ge R$ und $L\ne R$ erzeugen lediglich weitere rationale schwache
Ungleichungen beziehungsweise endlich viele strikte Zweige. Somit stimmen
`SAT` und `UNSAT` bei allen Erfüllbarkeits-, Folgerungs-, Maximums- und
Irredundanzanfragen über `Real` und über positive `Int`-Belegungen überein.

Eine Enumeration von Zahlenwerten bis zu einer willkürlichen Schranke wäre
dagegen nicht vollständig. Ein separater `Int`-Solver bleibt für Tests und
die unabhängige Validierung verfügbar; der Produktionsgenerator nutzt die
schnellere, nach obigem Argument exakte Real-Arithmetik.

### 3.2 Erfüllbarkeit und Folgerung

Ein System ist erfüllbar genau dann, wenn

\[
D\land F_s
\]

erfüllbar ist.

Für ein Atom $q$ gilt

\[
s\models q
\quad\Longleftrightarrow\quad
D\land F_s\land\neg q\text{ ist unerfüllbar}.
\]

Dabei wird negiert als

\[
\neg(L<R)\equiv L\ge R,
\qquad
\neg(L=R)\equiv L\ne R.
\]

Alle Folgerungsprüfungen müssen $D$ enthalten. Insbesondere dürfen die
gewünschten Aussagen $a>b,c,d$ nicht vorab als Annahmen in den Solver
eingesetzt werden; sonst würde die entscheidende Eigenschaft trivialerweise
für jedes erfüllbare System gelten.

Für viele Anfragen an dasselbe System wird ein inkrementeller Solver benutzt:
`D` und $F_s$ bleiben fest, und für jedes zu prüfende Atom wird
`push(); add(Not(atom)); check(); pop()` ausgeführt. Die Z3-Ausdrücke aller 567
Atome und ihrer Negationen sollten einmalig aufgebaut und wiederverwendet
werden.

## 4. Gültigkeitsprüfungen eines Systems

### 4.1 Eindeutig erzwungenes schwerstes Gewicht

Variable $i$ ist durch $s$ als eindeutig schwerste Variable erzwungen,
wenn

\[
s\models \bigwedge_{j\ne i}x_i>x_j.
\]

Für ein erfüllbares System kann höchstens eine Variable diese Eigenschaft
haben. Da Systeme ohnehin bis auf Umbenennung betrachtet werden, wird dieses
Symbol schon während der Erzeugung ohne Beschränkung der Allgemeinheit `a`
genannt. Setze

\[
A=(x_a>x_b)\land(x_a>x_c)\land(x_a>x_d),
\qquad
\neg A=(x_a\le x_b)\lor(x_a\le x_c)\lor(x_a\le x_d).
\]

Ein Kandidat hat genau dann das geforderte erzwungene Maximum `a`, wenn

\[
D\land F_s\land A\quad\text{SAT}
\]

und

\[
D\land F_s\land\neg A\quad\text{UNSAT}
\]

gelten. Die erste Anfrage beweist zugleich die Erfüllbarkeit; die zweite ist
der Folgerungstest $s\models A$. `A` ist dabei nur ein temporärer Zusatz der
SAT-Anfrage, niemals Bestandteil des Systems oder des Hintergrundbereichs.
Die Paarverschiedenheit garantiert zwar, dass jedes einzelne Modell ein
eindeutiges Maximum hat; erst der UNSAT-Test zeigt aber, dass dessen Name in
**allen** Modellen derselbe ist.

### 4.2 Irredundanz

Eine Relation $r\in s$ ist redundant genau dann, wenn

\[
s\setminus\{r\}\models r.
\]

Also ist ein System genau dann irredundant, wenn für jedes $r\in s$

\[
D\land F_{s\setminus\{r\}}\land\neg r
\]

erfüllbar ist. Das dabei erhaltene ganzzahlige Modell ist zugleich ein gut
prüfbares **Irredundanzzeugnis**: Es erfüllt den Hintergrund und alle übrigen
Relationen, verletzt aber die entfernte Relation.

Wichtig ist, Irredundanz nicht nur syntaktisch zu prüfen. Beispielsweise kann
eine Relation erst aus der Kombination zweier anderer Relationen folgen.

## 5. Gleichheit von Systemen und Symmetrien

### 5.1 Semantische Gleichheit

Ohne Umbenennung sind zwei Systeme informationsgleich, wenn sie auf dem
positiven Wertebereich dieselben Modelle haben:

\[
s\equiv t
\quad:\Longleftrightarrow\quad
D\models(F_s\leftrightarrow F_t).
\]

Eine Permutation $\pi\in S_4$ benennt die Variablen in jeder Relation um.
Die für das Ergebnis verwendete Äquivalenz ist

\[
s\sim t
\quad:\Longleftrightarrow\quad
\exists\pi\in S_4:\ \pi(s)\equiv t.
\]

Damit werden sowohl bloße Umbenennungen als auch verschiedene irredundante
Relationsbasen mit exakt demselben Informationsgehalt zusammengeführt. Falls
nur syntaktische Gleichheit modulo Umbenennung gewünscht wäre, könnte man die
semantische Abschlussphase unten weglassen; die hier gewählte Definition ist
die robustere Auslegung von „wirklich verschieden“ und „keine Information
verlieren“.

### 5.2 Schneller exakter Geometrieschlüssel

Die produktive Deduplizierung benötigt keine 567 Folgerungsanfragen pro
System. Sie benutzt die Geometrie der homogenen Theorie. Zu jeder Gleichung
gehört ihre Zeile $\delta=l-r$. Sei $E_s$ die Matrix dieser Zeilen und

\[
H_s=\ker(E_s)\subseteq\mathbb R^4.
\]

Die rationale reduzierte Zeilenstufenform `RREF(E_s)` beschreibt den
Gleichungszeilenraum eindeutig. Aus ihr wird eine rationale Basis
$v_1,\ldots,v_m$ von $H_s$ berechnet.

Jede strikte Ungleichung besitzt ebenfalls eine Normalenzeile $g=\delta$ mit
$g\cdot x<0$. Zusätzlich wird die Positivität durch die vier Normalen
$-e_a,-e_b,-e_c,-e_d$ einbezogen. Die Einschränkung von $g$ auf $H_s$ hat in
den freien Kernkoordinaten die Darstellung

\[
\widehat g=(g\cdot v_1,\ldots,g\cdot v_m)\in\mathbb Q^m.
\]

Dies ist keine orthogonale Projektion. Zwei Normalen, die sich nur um eine
Linearkombination der Gleichungszeilen unterscheiden, erhalten genau richtig
dieselbe Einschränkung auf $H_s$.

Der geschlossene primale Ungleichungskegel und sein hier mit festgelegter
Vorzeichenkonvention dualer beziehungsweise polarer Kegel sind

\[
K_s=\{x\in H_s:g\cdot x\le0\text{ für alle Ungleichungsnormalen }g\},
\]

\[
K_s^*=\operatorname{cone}_{\ge0}\{\widehat g:g\text{ ist eine
Ungleichungs- oder Positivitätsnormale}\}.
\]

Mehrfach vorkommende Strahlen werden primitiv normiert: Nenner werden
beseitigt und der gemeinsame ganzzahlige Teiler wird gekürzt, ohne das
Vorzeichen zu ändern. Ein Strahl ist nicht extrem und damit redundant, wenn
er im nichtnegativen Spann der übrigen Strahlen liegt. Dieser Test erfolgt
mit `Fraction`-Arithmetik exakt. Nach dem Satz von Carathéodory müssen in
Dimension $m\le4$ nur Teilmengen von höchstens $m$ Erzeugern geprüft werden.

Der nicht kanonisierte Theorie-Schlüssel ist

\[
T(s)=\bigl(\operatorname{RREF}(E_s),
           \operatorname{ExtRays}(K_s^*)\bigr),
\]

wobei Brüche als Zähler-Nenner-Paare und die primitiven Extremstrahlen
sortiert serialisiert werden.

Die entscheidende strikte Farkas-Alternative lautet für ein weiteres
projiziertes Funktional $h$ und einen strikt zulässigen Punkt $y_0$:

\[
h(y)<0\text{ für alle strikt zulässigen }y
\quad\Longleftrightarrow\quad
h\in K_s^*\setminus\{0\}.
\]

Die Richtung von rechts nach links folgt aus der nichtnegativen
Linearkombination der Normalen. Liegt $h$ nicht im geschlossenen Kegel
$K_s^*$, trennt ein Funktional beide und liefert einen Punkt mit
$\widehat g\cdot y\le0$ für alle Erzeuger, aber $h(y)>0$. Eine hinreichend
kleine Beimischung von $y_0$ macht alle Prämissen strikt, ohne $h(y)>0$ zu
zerstören. Damit bestimmen die Extremstrahlen exakt alle strikten linearen
Folgerungen.

Dieser Schlüssel ist für jeden bereits als erfüllbar geprüften Kandidaten
vollständig. Ohne `Distinct` ist die Menge der positiven reellen Modelle die
relative offene Innenseite von $K_s$ in $H_s$; wegen gemeinsamer strikter
Erfüllbarkeit ist ihr Abschluss genau $K_s$. Der Gleichungsraum und die
Extremstrahlen des dualen Kegels bestimmen diesen abgeschlossenen Kegel und
damit seine relative Innenseite eindeutig. `Distinct` entfernt daraus nur
die endlich vielen rationalen Hyperebenen $x_i=x_j$. Da ein akzeptierter
Kandidat mindestens einen paarweise verschiedenen Punkt besitzt, liegt seine
offene Modellmenge in keiner dieser Hyperebenen; die verbleibenden
`Distinct`-Punkte sind dicht und haben denselben Abschluss. Nach Abschnitt
3.1 gilt dasselbe für die positiven ganzzahligen Modelle. Daher gilt für
erfüllbare Kandidaten

\[
T(s)=T(t)\quad\Longleftrightarrow\quad s\equiv t.
\]

Alle Kandidaten erzwingen bereits `a` als Maximum. Eine semantische
Umbenennung zwischen zwei solchen Kandidaten muss deshalb `a` festlassen. Der
produktive kanonische Schlüssel ist folglich

\[
\operatorname{theorykey}(s)
=\min_{\pi\in S_{\{b,c,d\}}}T(\pi(s)).
\]

Die Ergebnistabelle verwendet den **vollständigen** rationalen Schlüssel,
nicht dessen Hash. Erst für JSON wird seine eindeutige kompakte
Serialisierung mit SHA-256 zu `semantic_key` gehasht. Eine Hashkollision kann
somit die Deduplizierung nicht verfälschen.

### 5.3 Unabhängiger Referenzschlüssel über alle 567 Atome

Für ein System wird sein Abschluss bezüglich des endlichen
Relationsuniversums berechnet:

\[
\operatorname{Cl}(s)=\{q\in R:s\models q\}.
\]

Er wird als 567-Bit-Vektor in der festen Reihenfolge von $R$ gespeichert.
Für Systeme, deren Relationen aus $R$ stammen, ist diese Signatur vollständig:

\[
\operatorname{Cl}(s)=\operatorname{Cl}(t)
\quad\Longleftrightarrow\quad
s\equiv t.
\]

Die Rückrichtung ist unmittelbar. Für die Hinrichtung gilt: Jede Relation aus
$s$ liegt in $\operatorname{Cl}(s)=\operatorname{Cl}(t)$, also impliziert
$t$ ganz $s$. Symmetrisch impliziert $s$ ganz $t$.

Auch dieser Schlüssel wird nach Fixierung des Maximums `a` unter den sechs
Permutationen von `b`, `c`, `d` kanonisiert:

\[
\operatorname{sig}(s)
=\min_{\pi\in S_{\{b,c,d\}}}\pi(\operatorname{Cl}(s)).
\]

Die Permutation wirkt dabei auf den 567 Bitpositionen über dieselbe
vorberechnete Relationsabbildung wie bei der syntaktischen Kanonisierung.
Der resultierende Bitvektor wird als Hash-Tabellenschlüssel verwendet. Ein
Im Referenzpfad darf SHA-256 als stabile ID dienen; intern muss bei einer theoretisch
möglichen Hashkollision zusätzlich der volle Bitvektor verglichen werden.

Diese Hash-Tabelle gehört ausschließlich zur Closure-Referenzimplementierung.
`generate_s.py` dedupliziert mit dem vollständigen Geometrieschlüssel aus
Abschnitt 5.2; dessen SHA-256-Digest wird erst bei der JSON-Ausgabe als
`semantic_key` erzeugt.

#### Gegenmodell-Berechnung des Referenzabschlusses

Naiv wären pro System 567 Unerfüllbarkeitsprüfungen nötig. Das folgende
Gegenmodell-Batching reduziert ihre Anzahl, bleibt aber erheblich teurer als
der Geometrieschlüssel:

```text
closure(F):
    solver-Basis := D und F
    undecided := alle 567 Atome
    entailed  := leere Bitmenge

    M := ein Modell der solver-Basis
    entferne aus undecided jedes Atom, das in M falsch ist

    solange undecided nicht leer ist:
        wähle q aus undecided
        prüfe solver-Basis und not q
        falls UNSAT:
            setze das Bit von q in entailed
            entferne q aus undecided
        sonst:
            lies das Gegenmodell M
            entferne jedes in M falsche Atom aus undecided

    return entailed
```

Ein Gegenmodell widerlegt häufig gleichzeitig Hunderte noch offene
Folgerungskandidaten. Ein wirklich impliziertes Atom kann nie auf diese Weise
entfernt werden, sodass das Verfahren exakt bleibt. Seine Solveranfragen
nutzen ebenfalls die nach Abschnitt 3.1 exakte Real-Arithmetik.

### 5.4 Die Namenskonvention für `b`, `c`, `d`

Da das erzwungene Maximum bereits `a` heißt, bleiben sechs Permutationen der
unteren Variablen. Zulässig sind gemäß Eigenschaft 6 nur die
Benennungen, bei denen keine der folgenden Aussagen aus dem System folgt:

\[
b>c,\qquad d>c,\qquad d>b.
\]

Eine solche Benennung existiert immer: Die erzwungenen strikten Vergleiche
unter $b,c,d$ bilden wegen der Erfüllbarkeit eine azyklische partielle
Ordnung. Eine topologische Sortierung kann von groß nach klein mit den Namen
$c,b,d$ belegt werden. Die semantische Signatur wird unabhängig davon unter
allen sechs Permutationen gebildet. Für den tatsächlich ausgegebenen
Repräsentanten wird unter den zulässigen Benennungen die lexikographisch
kleinste sortierte Relationsliste gewählt.

Diese Regel ist reine Kanonisierung. Sie darf keine Informationsklasse aus
dem Ergebnis entfernen.

## 6. Symmetriearme vollständige Erzeugung

Die direkte Enumeration umfasst

\[
\binom{567}{2}=160\,461
\quad\text{Paare und}\quad
\binom{567}{3}=30\,220\,155
\quad\text{Tripel}.
\]

Über 30 Millionen Tripel einzeln an Z3 zu schicken wäre unnötig. Folgendes
Verfahren fixiert zuerst das Maximum `a`, reduziert dann unter $S_3$ und
entscheidet viele mögliche dritte Relationen gemeinsam anhand weniger
Gegenmodelle.

Setze

\[
R_a=\{r\in R:D\land A\land r\text{ ist erfüllbar}\}.
\]

Ein gültiges, bereits auf Maximum `a` umbenanntes System kann keine Relation
außerhalb von $R_a$ enthalten. Der Filter ist daher vollständigkeitsneutral.
Für das in Abschnitt 2 definierte Universum und den `Distinct`-Hintergrund
gilt als Regressionstest

\[
|R_a|=454.
\]

### 6.1 Vorberechnung der Gruppenwirkung

Die sechs Permutationen von `b`, `c`, `d` lassen `a`, $D$, $A$ und $R_a$
invariant. Für jede davon und jeden Relationsindex wird einmal berechnet, auf
welchen kanonisch normalisierten Relationsindex er abgebildet wird:

```text
perm_index[permutation][relation_index]
```

Der syntaktische Orbit-Schlüssel eines Systems ist das Minimum der sechs
jeweils sortierten permutierten Indextupel. Ein Tupel wird nur untersucht,
wenn es selbst dieser Schlüssel ist. Außerdem muss bei einem kanonischen
Tupel dessen erster Relationsindex ein Repräsentant seines Einzelorbits sein;
dadurch können die äußeren Schleifen weiter verkürzt werden.

Als Regressionstest ergeben sich auf $R_a$ genau

- 102 Orbits einzelner Relationen,
- 17 811 Orbits von Relationspaaren und
- 2 595 782 Orbits von Relationstripeln.

Diese Orbit-Kanonisierung ist nur ein früher, billiger Filter. Die endgültige
Gleichheit wird weiterhin durch den semantischen Abschluss entschieden.

### 6.2 Paare

Für jedes kanonische Indexpaar $P=(i,j)$ wird in dieser Reihenfolge geprüft:

1. `SAT(D and F_P and A)`; sonst ist kein gültiges System mit diesem Paar
   möglich.
2. `UNSAT(D and F_P and not A)`; genau dann erzwingt das Paar `a` als
   Maximum.
3. `SAT(D and r_i and not r_j)` und
   `SAT(D and r_j and not r_i)`; genau dann ist das Paar irredundant.

Besteht es alle Tests, wird es als logischer Ergebniskandidat an die
semantische Abschlussphase übergeben.

### 6.3 Gegenbeispielgesteuerte Tripel aus Paarpräfixen

Jedes irredundante, erfüllbare Tripel besitzt ausschließlich erfüllbare,
intern irredundante Zweier-Teilsysteme. Denn würde in einem solchen Paar eine
Relation aus der anderen folgen, bliebe sie auch im ganzen Tripel redundant.

Die kanonischen Tripel werden nach ihrem Präfix $P=(i,j)$ gruppiert. Zu einem
Präfix sei $U_P$ die Menge aller Indizes $k>j$, für die $(i,j,k)$ bereits der
syntaktische $S_3$-Orbit-Schlüssel ist. Vor der Verarbeitung von $U_P$ werden
die zwei notwendigen Präfixbedingungen geprüft:

1. $D\land F_P\land A$ ist erfüllbar.
2. Keine der beiden Präfixrelationen folgt unter $D$ aus der anderen.

Nun definiere

\[
B_P=D\land F_P\land\neg A.
\]

Gesucht sind exakt die dritten Relationen $r_k$ mit

\[
B_P\land r_k\quad\text{UNSAT},
\]

denn genau diese sperren gemeinsam mit dem Präfix alle Modelle, in denen `a`
nicht oben liegt. Statt für jedes $k$ eine eigene Anfrage auszuführen, werden
Gegenmodelle gebündelt ausgewertet:

```text
dominance_completions(P, U):
    solver := inkrementeller Solver für B_P
    result := solver.check()

    falls result == UNSAT:
        liefere alle k aus U
        return

    M := solver.model()
    entferne aus U jedes k, für das M die Relation r_k erfüllt

    solange U nicht leer ist:
        entnimm ein k aus U
        prüfe per push/pop: B_P und r_k

        falls UNSAT:
            liefere k
        sonst:
            M := das gefundene Modell von B_P und r_k
            entferne aus U jedes q, für das M die Relation r_q erfüllt
```

Die Entfernung ist exakt: Erfüllt ein Modell von $B_P$ eine Relation $r_q$,
so ist dieses Modell bereits ein Zeuge für die Erfüllbarkeit von
$B_P\land r_q$; $q$ kann das falsche Maximum also nicht ausschließen. Eine in
diesem Modell falsche Relation bleibt lediglich unentschieden. Jede
Schleifenrunde entfernt mindestens den ausgewählten Index, daher terminiert
das Verfahren und liefert genau alle Dominanzvervollständigungen.

Für jedes gelieferte $k$ wird anschließend noch

1. `SAT(D and F_P and r_k and A)` und
2. die volle Irredundanz des Tripels durch drei Gegenmodellanfragen

geprüft. Der erste Test ist nötig, weil `UNSAT(B_P and r_k)` auch durch einen
Widerspruch zwischen Präfix und dritter Relation entstehen könnte. Gemeinsam
mit dem Dominanztest beweist er Erfüllbarkeit und $F_{P\cup\{r_k\}}\models A$.

Jeder gültige Tripelorbit wird untersucht: Nach der Umbenennung seines
Maximums in `a` besitzt er einen eindeutigen syntaktischen $S_3$-Orbit-Schlüssel
$(i,j,k)$, der im Paarpräfix $(i,j)$ erscheint. Die Präfixfilter können ein
irredundantes, erfüllbares Tripel nicht entfernen, und sein drittes Atom ist
notwendig eine Dominanzvervollständigung.

### 6.4 Semantisches Zusammenführen und Repräsentantenwahl

Für jeden logisch gültigen Kandidaten berechnet der
`TheoryCanonicalizer` den in Abschnitt 5.2 beschriebenen exakten
Geometrieschlüssel. Dafür sind keine weiteren Solveranfragen nötig. Eine
Tabelle

```text
best_by_theory_key[canonical_theory_key] = representative
```

behält pro Informationsklasse genau einen Repräsentanten. Gibt es mehrere
irredundante Basen derselben Klasse, gewinnt deterministisch

1. die mit weniger Relationen und danach
2. die lexikographisch kleinere kanonische Relationsliste.

Dadurch wird beispielsweise eine Informationsklasse nicht zusätzlich als
Dreiersystem ausgegeben, wenn dieselbe Information bereits durch ein
irredundantes Zweiersystem dargestellt werden kann.

Jeder Worker dedupliziert zunächst lokal; beim Zusammenführen gelten dieselben
Auswahlregeln. Der 567-Bit-Closure aus Abschnitt 5.3 kann anschließend als
unabhängige Verifikation berechnet werden, gehört aber nicht zum regulären
Generationspfad.

## 7. Gesamtalgorithmus

In kompakter Form:

```text
1. Erzeuge und sortiere das primitive Relationsuniversum R.
2. Baue die Real-Ausdrücke, D und A; filtere R auf das a-kompatible R_a.
3. Erzeuge die sechs S3-Abbildungstabellen für R_a und für das volle R.
4. Erzeuge syntaktische Paarorbits; prüfe SAT, erzwungenes a und Irredundanz.
5. Gruppiere kanonische Tripel nach ihren Paarpräfixen.
6. Filtere Präfixe auf a-Kompatibilität und notwendige Paar-Irredundanz.
7. Ermittle mögliche dritte Relationen durch Gegenmodell-Batching gegen not A.
8. Prüfe die gelieferten Tripel vollständig auf SAT und Irredundanz.
9. Berechne für logische Ergebniskandidaten den kanonischen RREF-/Kegelschlüssel.
10. Behalte pro vollständigem Theorie-Schlüssel den besten Repräsentanten und
    erfülle für die Ausgabe die Namenskonvention für b,c,d.
11. Sortiere alle Repräsentanten deterministisch und schreibe das JSON atomar
    über eine temporäre Datei.
```

Die Reihenfolge „billige Symmetrietests und Modellauswertung vor einzelnen
UNSAT-Anfragen“ ist für die Laufzeit entscheidend. Geometrieschlüssel werden
erst nach allen Gültigkeitsfiltern berechnet; Closure-Schlüssel nur in der
separaten Verifikation.

Für Parallelisierung teilt `generate_s.py` die Tripel nach dem ersten
kanonischen Relationsindex in Chunks. Jeder Prozess erzeugt einen eigenen
Generator samt Z3-Kontext und dedupliziert seinen Chunk bereits lokal. Der
Hauptprozess vereinigt die Dictionaries mit derselben deterministischen
Repräsentantenwahl. Z3-Kontexte werden nicht zwischen Threads oder Prozessen
geteilt.

## 8. JSON-Format

`generate_s.py` schreibt Metadaten und sparse Koeffizienten-Mappings. Ein
vollständiges Ein-System-Beispiel im tatsächlichen Schema ist:

```json
{
  "metadata": {
    "schema_version": 1,
    "variables": ["a", "b", "c", "d"],
    "domain": "pairwise_distinct_positive_integers",
    "relation_normalization": "primitive_coefficients",
    "equivalence": "same_solution_set_up_to_variable_permutation; winner_named_a",
    "redundancy": "logical_entailment_over_the_domain",
    "relation_universe_size": 567,
    "a_compatible_relation_count": 454,
    "system_count": 1,
    "structural_systems_before_semantic_deduplication": 1
  },
  "systems": [
    {
      "relations": [
        {
          "left": {"c": 1, "d": 1},
          "operator": "<",
          "right": {"a": 1},
          "display": "c + d < a"
        },
        {
          "left": {"b": 1, "d": 1},
          "operator": "<",
          "right": {"a": 1},
          "display": "b + d < a"
        }
      ],
      "id": "s000001",
      "semantic_key": "37b62315cf537d40526afbdcc3d38b7c9fc8574ef28abb34bb20e67d7247c89b"
    }
  ]
}
```

`left` und `right` bilden nur die vorkommenden Variablennamen auf ihre positive
Multiplizität ab; Koeffizient null wird ausgelassen. Die beiden Mappings und
`operator` sind die verbindliche maschinenlesbare Relation. `display` wird
daraus erzeugt und dient der direkten Lesbarkeit. Beide Seiten müssen
nichtleer, disjunkt und von Koeffizientensumme höchstens 3 sein. Relationen
stehen in kanonischer Sortierung.

`id` ist eine nach der deterministischen Gesamtsortierung vergebene laufende
Kennung. `semantic_key` ist der SHA-256-Digest der kompakten, eindeutigen
JSON-Serialisierung des kanonischen RREF-/Extremstrahl-Schlüssels, nicht des
567-Bit-Closures. Intern erfolgt die Deduplizierung weiterhin mit dem vollen
Schlüssel. Die beiden Zähler in den Metadaten unterscheiden die Anzahl der
aus dem Generator kommenden strukturellen Systeme von der Anzahl der danach
verbleibenden semantischen Klassen. Geschrieben wird zunächst in eine
`.tmp`-Datei, die anschließend atomar den Zielpfad ersetzt.

## 9. Korrektheit

### 9.1 Terminierung

Das Relationsuniversum, die Gruppenwirkung und die Mengen der Zwei- und
Dreiersysteme sind endlich. Jede Solver-Anfrage liegt in entscheidbarer
quantorenfreier linearer reeller Arithmetik. Im Gegenmodell-Batching wird in
jeder Runde mindestens ein Kandidat entfernt. RREF, rationale
Kegelberechnung und die Carathéodory-Teilmengentests arbeiten auf endlichen
Mengen. Der Algorithmus terminiert daher.

### 9.2 Korrektheit jedes ausgegebenen Systems

Für jeden ausgegebenen Repräsentanten wurden exakt geprüft:

- zwei oder drei verschiedene zulässige primitive Relationen,
- Erfüllbarkeit über positiven, paarweise verschiedenen natürlichen Zahlen,
- Folgerung $a>b,c,d$,
- die Namenskonvention unter $b,c,d$,
- Nichtfolgerung jeder Relation aus den jeweils übrigen Relationen.

Damit erfüllt jedes ausgegebene System die Eigenschaften 1 bis 9 unter der in
Abschnitt 1 festgelegten Interpretation.

### 9.3 Vollständigkeit

Jede zulässige Relation besitzt eine primitive Normalform in $R$. Ein
gültiges System kann auf sein erzwungenes Maximum `a` umbenannt werden; dann
liegen alle seine Relationen in $R_a$. Ein gültiges Zweiersystem erscheint in
der vollständigen Paarorbit-Erzeugung. Der kanonische Schlüssel jedes gültigen
Dreiersystems erscheint bei genau einem kanonischen Paarpräfix. Dessen
notwendige Präfixtests bestehen, und die dritte Relation wird vom
Gegenmodellverfahren genau deshalb geliefert, weil das Gesamtsystem
$\neg A$ ausschließt. Syntaktische Orbit-Kanonisierung entfernt nur
Umbenennungen. Die anschließenden Tests sind äquivalente logische Kriterien
für Erfüllbarkeit, Irredundanz und das erzwungene Maximum. Somit erreicht jeder
gültige semantische Systemorbit die Ergebnistabelle.

### 9.4 Keine Doppelungen

Nach Abschnitt 5 sind zwei erfüllbare Kandidaten genau dann
informationsgleich modulo Umbenennung, wenn ihre kanonischen rationalen
RREF-/Extremstrahl-Schlüssel gleich sind. Die Tabelle enthält pro
**vollständigem** Schlüssel genau einen Eintrag. Der erst danach gebildete
SHA-256-Digest nimmt an dieser Entscheidung nicht teil. Daher enthält das
Ergebnis keine zwei äquivalenten Systeme. Der unabhängige Closure-Satz aus
Abschnitt 5.3 liefert dieselbe Äquivalenz als Kontrollweg.

## 10. Validierung und Tests

Mindestens folgende automatisierte Prüfungen sollten Teil der Implementierung
sein:

1. **Universum:** 567 Atome, davon 378 Ungleichungen und 189 Gleichungen;
   jede Relation ist primitiv, gekürzt und erfüllt die Seitengrenzen.
2. **Maximumfilter:** $R_a$ enthält 454 Relationen und ist unter allen sechs
   Permutationen der unteren Variablen abgeschlossen.
3. **Gruppenwirkung:** Die Orbitzahlen 102, 17 811 und 2 595 782 auf $R_a$
   stimmen für Systeme der Größen eins, zwei und drei.
4. **Metamorpher Symmetrietest:** Alle sechs Umbenennungen von `b`, `c`, `d`
   liefern denselben kanonischen Theorie- und Closure-Schlüssel. Nach einer beliebigen der 24
   Umbenennungen und erneuter Benennung des Maximums als `a` gilt dasselbe.
5. **Real/Integer:** Repräsentative SAT-, UNSAT-, Folgerungs- und
   Irredundanzanfragen liefern mit `Real` und `Int` dasselbe Ergebnis.
6. **Ausgabe-SAT:** Jedes JSON-System ist mit Positivität und `Distinct` in
   einem frischen `Int`-Solver erfüllbar.
7. **Maximum:** Für jedes Ausgabesystem sind die drei Formeln mit
   $a\le b$, $a\le c$, $a\le d$ unerfüllbar.
8. **Namenskonvention:** Keines der drei verbotenen unteren
   Größenverhältnisse ist eine Folgerung.
9. **Irredundanz:** Nach Entfernen jeder Relation erzeugt ein frischer Solver
   ein positives, paarweise verschiedenes Gegenmodell, das die entfernte
   Relation verletzt.
10. **Dominanz-Batching:** Auf kleinen Relationsausschnitten und zufälligen
   Paarpräfixen stimmt die gelieferte Menge exakt mit separaten Prüfungen von
   $B_P\land r_k$ für jedes $k$ überein.
11. **Doppelte Semantikprüfung:** Für bekannte alternative Relationsbasen
    und systematische Stichproben gilt: Theorie-Schlüssel sind genau dann
    gleich, wenn die kanonischen 567-Bit-Closures gleich sind.
12. **JSON:** Metadaten, sparse Mappings, `display`, fortlaufende IDs und der
    SHA-256-Digest stimmen mit einer unabhängigen Neuberechnung überein.
13. **Brute-Force-Gegenprobe:** Für kleine Gewichte, etwa 1 bis 8,
   werden zufällige Kandidaten und alle gespeicherten Zeugen direkt
   ausgewertet. Dies ersetzt keinen SMT-Beweis, findet aber
   Kodierungsfehler sehr zuverlässig.
14. **Reproduzierbarkeit:** Zwei Läufe mit anderer Workerzahl erzeugen nach
    Sortierung byte-identisches JSON und denselben Gesamt-Hash.
