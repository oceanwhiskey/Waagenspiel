# Waagenspiel

Es sei $G = \{a, b,c ,d\}\subset \mathbb {N}$ eine Menge von Gewichten mit $a, b, c, d > 0$.
Wir untersuchen nun bestimmte Systeme von Relationen bezüglich $G$. Die gesuchte Menge von Systemen bezeichnen wir mit $S$. Ein Elemente aus $S$ bezeichnen wir mit $s$. $s$ enthält Relationen $r_i$ und wir schreiben z.B. $s = \{r_1, r_2, r_3\}$.
Gesucht sind alle möglichen verschiedenen Systeme von Relationen, die diese Eigenschaften erfüllen.

# Eigenschaften der Systeme in $S$

1. Ein System $s\in S$ hat entweder zwei Relationen oder drei Relationen. Also $|s|\in \{2, 3\}$.
2. Eine Relation ist entweder eine Gleichung oder eine "kleiner als"-Relation.
3. Auf beiden Seite jeder Relation steht mindestens ein Element aus $G$.
4. Dasselbe Element aus $G$ steht niemals auf beiden Seiten einer Relation. Das bedeutet, dass eine Relation "gekürzt" ist um dieselben Elemente auf beiden Seiten.
5. Es lässt sich für jedes System eindeutig genau ein Element ermitteln, das am schwersten ist. Dieses Element sei immer $a$. Es gilt also $a > b, c, d$.
6. Die Systeme in $S$ sind alle verschieden. Insbesondere lassen sich zwei Systeme durch vertauschen der Bezeichnungn aus $G$ nicht ineinander überführen. Um das sicherzustellen können wir ohne Beschränkung der Allgemeinheit davon ausgehen, dass Folgendes immer gilt: $a > b, c, d$. Gegeben $s$ folgt niemals $b>c$ oder $d>c$ oder $d>b$.
7. Innerhalb einer Relation kann ein Element auch mehrfach auf einer Seite auftreten.
8. Es können maximal drei Elemente aus $G$ auf einer Seite einer Relation stehen.
9. Es gibt keine Relationen, die keinen Mehrwert bringen. Wenn ich eine Relation weglasse und dadurch keine Information verliere, dann soll die Relation im System nicht vorkommen.



# Problem

Gesucht ist die Menge $S$.
Dafür soll zunächst mathematisch definiert werden, wann zwei Systeme wirklich verschieden sind im Sinne der Definition eines Systems aus $S$. Es muss programmatisch erkannt werden können, ob zwei Systeme gleich sind.

Dann muss ein Programm entwickelt werden, das ermittelt, ob ein System eine eindeutige Lösung hat.

Auf dieser Basis soll dann $S$ in einem geeigneten json-Format generiert werden.

Alle Programme sollen in Python entwickelt sein. Alle auf dem Weg entstandenen mathematischen Definitionen/Beweise/Ideen sollen in md-Dateien dokumentiert werden.