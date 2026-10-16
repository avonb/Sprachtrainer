# Vokabeln und Lernstand

Die Entwicklungsdatenbank enthält eine persönliche Sammlung für einen Lernenden.
Die spätere Anmeldung schützt diese Sammlung. Mehrbenutzerbetrieb und getrennte
Lernstände je Abfragerichtung sind noch nicht vorgesehen.

## Daten

- `vocabulary`: persische Schreibweise, deutsche Bedeutung, optionale Umschrift,
  persischer/deutscher Beispielsatz und Notizen. Texte werden als Unicode NFC
  gespeichert; persische Zeichen und Worttrenner bleiben erhalten.
- `learning_state`: nächster Wiederholungstermin, Intervall in Tagen, erfolgreiche
  Wiederholungen seit dem letzten Fehler, Fehlerzahl, letzter Termin und Revision.
- `reviews`: einzelne Bewertungen mit Zeitstempel und daraus berechnetem Termin.
- `tags`: gemeinsame Tag-Namen, beispielsweise `alltag`, `verben` oder `lektion 1`.
- `vocabulary_tags`: Zuordnung zwischen Vokabeln und Tags. Eine Vokabel kann
  beliebig viele Tags haben, und ein Tag kann mehreren Vokabeln zugeordnet sein.

Tag-Namen werden mit Unicode NFC, vereinheitlichten Leerzeichen und ohne
Unterscheidung von Groß-/Kleinschreibung gespeichert. Sie sind 1 bis 80 Zeichen
lang. Doppelte Zuordnungen werden verhindert. Entfernen eines Tags von einer
Vokabel verändert weder andere Vokabeln noch ihren Lernstand. Archivierte Wörter
behalten ihre Tags. Unbenutzte Tags bleiben im Katalog zur Wiederverwendung.

Zeitstempel sind UTC Unix-Sekunden. Neue Wörter sind sofort fällig. Archivierte
Wörter erscheinen nicht in Wiederholungen; Wiederherstellen erhält den Verlauf.
Bearbeiten von Wort und Bedeutung verändert den Lernstand nicht. `save` ersetzt
alle Textfelder; für einzelne Änderungen zuerst den bisherigen Datensatz laden.
Vokabeln werden nicht automatisch anhand ihrer Schreibweise zusammengeführt,
damit verschiedene Bedeutungen eines Wortes möglich bleiben.

## Wiederholungen

Die erste Version nutzt nachvollziehbare Intervallregeln, kein FSRS/SM-2:

| Bewertung | Nächste Wiederholung |
|---|---|
| `again` / nochmal | in 10 Minuten; Erfolgsserie zurücksetzen, Fehlerzahl erhöhen |
| `hard` / schwer | bisheriges Tagesintervall × 1,2, aufgerundet; mindestens 1 Tag |
| `good` / gut | zuerst 1 Tag, danach 3 Tage, anschließend Intervall verdoppeln |
| `easy` / leicht | bisheriges Tagesintervall × 3; mindestens 4 Tage |

Tagesintervalle sind auf 365 Tage begrenzt und beginnen beim Bewertungszeitpunkt.
Eine spätere Änderung des Algorithmus kann den gespeicherten Verlauf nutzen.
Audio, Antworten und Gesprächsinhalte werden nicht gespeichert.

## Interne Verwendung

`src/learning.py` bietet `VocabularyStore(db)` für das D1-Binding:

- `save`, `get`, `archive`: Wörter anlegen, vollständig bearbeiten und archivieren.
- `due`: fällige Wörter, älteste Fälligkeit zuerst, maximal 100 pro Aufruf.
- `state`, `history`: aktueller Lernstand und die letzten Bewertungen.
- `review`: Bewertung speichern und den Lernstand atomar aktualisieren.
- `add_tag`, `remove_tag`, `tags`: Tags einzeln zuordnen, entfernen und lesen.
- `list_tags`: Tag-Katalog einschließlich Anzahl zugeordneter aktiver Vokabeln.

`get`, `save`, `archive` und `due` liefern zusätzlich `tags` als sortierte Liste.
Die Textbearbeitung mit `save` erhält bestehende Tag-Zuordnungen. Mit
`due(tag='alltag')` lassen sich fällige Vokabeln nach einem Tag filtern. Ohne
Tag-Filter werden alle fälligen Vokabeln berücksichtigt.

Jede Antwort sollte eine stabile `review_id` erhalten. Ein erneuter Aufruf mit
derselben ID, Vokabel und Bewertung liefert das bereits gespeicherte Ergebnis.
Dies verhindert Doppelzählungen bei wiederholten MCP-Anfragen. Eine konkurrierende
andere Bewertung mit veralteter Revision wird abgewiesen; dann neu laden und
gegebenenfalls erneut versuchen. Alte Zeitstempel werden ebenfalls abgewiesen.

Die Datenverwaltung ist noch nicht über HTTP/MCP aufrufbar. Sie soll erst hinter
der Anmeldung erreichbar werden. `/health/db` liefert weiterhin nur eine Anzahl.

## Prüfen und migrieren

```sh
python -m unittest discover -s tests -v
npm run db:migrate:local
npm run build
```

Die Tests wenden die Migrationen auf SQLite an und prüfen auch vorhandene Wörter,
Bewertungswiederholungen, Fälligkeiten und die atomare Aktualisierung per Trigger.
Die Remote-Migration wird ausdrücklich mit `npm run db:migrate:remote` angewendet.

Mit Cloudflare-Zugang prüft `python scripts/check_d1.py` die Verwaltung zusätzlich
gegen die konfigurierte Entwicklungsdatenbank. Der Test legt eine Testvokabel an,
prüft Speicherung, Tags und Wiederholungen über mehrere API-Aufrufe und entfernt seine
Datensätze anschließend. Er ist bewusst kein Teil der normalen Testausführung.
