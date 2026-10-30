# anilist-crunchyrool-mapping

Dieses Skript wandelt lokal gespeicherte Crunchyroll-CMS-JSON-Antworten in
eine normalisierte JSON-Datenbank um. Es ruft selbst keine API auf, erkennt
nicht die aktuell abgespielte Folge und greift nicht auf Videostreams zu.

## Daten beschaffen

Der bisher funktionierende Weg ist, die Antworten im Browser mitzuschneiden.
Direkte `curl`-Anfragen an Crunchyroll wurden mit `403 Forbidden` und einer
Cloudflare-Challenge blockiert; der Parser bietet keinen alternativen
Downloadweg.

1. Öffne Crunchyroll in Chrome und rufe die gewünschte Serie beziehungsweise
   eine Folge auf.
2. Öffne die Entwicklerwerkzeuge (`F12`) und den Tab **Network**. Aktiviere
   **Preserve log**, wähle **Fetch/XHR** und lade die Seite neu.
3. Öffne die passenden Anfragen und kopiere im Tab **Response** den
   Antwortinhalt. Speichere jede Antwort als eigene `.json`-Datei. Gesucht
   werden Antworten mit Serien-, Staffel- oder Episodenobjekten, häufig in
   einem `data`-Array.
4. Für weitere Episodenseiten scrolle in Crunchyroll weiter, sodass der
   Browser die nächste Seite lädt, und speichere auch deren Antwort. Ein
   `next_cursor` allein lädt keine weitere Seite; das Skript speichert ihn nur
   als Hinweis.

Bei den bisher untersuchten Anfragen waren unter anderem diese Pfade zu sehen
(IDs und Locale durch die Werte aus deinen Browser-Anfragen ersetzen):

```text
/content/v2/cms/objects/{EPISODE_ID}?locale=de-DE
/content/v2/cms/series/{SERIES_ID}?locale=de-DE
/content/v2/cms/series/{SERIES_ID}/seasons?force_locale=ja-JP&locale=de-DE
```

Entscheidend ist der JSON-Inhalt der **Response**, nicht ein kopierter
cURL-Befehl oder eine HAR-Datei. Veröffentliche keine HAR-Dateien oder
Anfrage-Header: Sie können Sitzungscookies oder andere vertrauliche
Anmeldedaten enthalten.

## Laufende Metadaten mit einem Skript oder Plugin mitlesen

Mit einem aktiven Datenstrom ist hier der laufende **HTTP-Verkehr der
Metadaten** im eigenen Browser-Tab gemeint, nicht der Video-/Audiostream.
JSON-Antworten lassen sich nach Abschluss einer Anfrage auslesen; das ist
kein Zugriff auf einzelne Video-Pakete oder DRM-geschützte Inhalte.

Unter `examples/devtools-extension/` liegt ein kleines Chrome-DevTools-Plugin.
Es verwendet die Network-Schnittstelle der Entwicklerwerkzeuge statt eigener
API-Anfragen. Dadurch bleiben Anmeldung und Anfragen beim normalen
Crunchyroll-Browserablauf. Das Beispiel umgeht keine Zugriffsbeschränkungen.

### Beispiel installieren und verwenden

1. Öffne `chrome://extensions` und aktiviere den **Entwicklermodus**.
2. Klicke **Entpackte Erweiterung laden** und wähle den Ordner
   `examples/devtools-extension/`.
3. Öffne auf deinem Crunchyroll-Tab die Entwicklerwerkzeuge neu und wähle
   das zusätzliche Panel **Crunchyroll CMS**; gegebenenfalls liegt es unter
   dem Überlaufmenü `>>`.
4. Lade erst danach die Crunchyroll-Seite neu. Öffne eine Serie oder Folge
   und lasse weitere Episodenlisten über die Oberfläche laden.
5. Klappe im Panel eine erfasste Antwort auf. **JSON speichern** lädt nur
   deren JSON-Inhalt herunter. Diese Dateien kannst du anschließend wie
   unten beschrieben an den Python-Parser übergeben.

Bereits vor dem Öffnen des Panels abgeschlossene Anfragen werden nicht
nachträglich eingelesen. Die Aufzeichnung läuft nur mit geöffneten DevTools;
beim Schließen gehen die nicht gespeicherten Anzeigen verloren.

### Wie das Skript funktioniert und in ein Plugin passt

`manifest.json` registriert `devtools.html` als DevTools-Seite.
`devtools.js` erstellt das Panel und registriert beim ersten Öffnen einen
Listener auf `chrome.devtools.network.onRequestFinished`. Dieser filtert
Crunchyroll-Adressen unter `/content/v2/cms/` und liest mit
`request.getContent(...)` die Antwort. `/videos/`-Anfragen werden ausgeschlossen.
Base64-kodierte Antworten werden vor dem JSON-Parsing dekodiert. HTTP-Fehler,
fehlende Inhalte und ungültiges JSON erscheinen als Meldung im Panel.

Für ein eigenes DevTools-Plugin kannst du diesen Listener übernehmen und
die gelesenen Objekte statt der Vorschau an deine Normalisierung weitergeben.
Ein normales Content-Script hat dagegen **keinen** Zugriff auf
`chrome.devtools.network`. Auch `chrome.webRequest` stellt in Chrome nicht
einfach die Response-Bodies bereit. Ein nachträglich in der Seitenkonsole
eingesetztes Skript kann bereits abgeschlossene Antworten nicht zurückholen.

Das Beispiel liest nur zukünftige CMS-Antworten, verändert keine Requests und
sendet nichts an externe Dienste. Es erkennt noch nicht zuverlässig, welche
der geladenen Folgen tatsächlich abgespielt wird: Auch Vorschauen und
Episodenlisten erzeugen Anfragen. Dafür muss ein späteres Plugin die Daten
zusätzlich mit der aktuellen Episoden-ID beziehungsweise Navigation abgleichen.
Die Live-Erfassung ist ein Integrationsbeispiel, keine Zusage, dass
Crunchyroll seine Endpunkte unverändert beibehält.

## Datenbank erstellen

Übergib alle gespeicherten JSON-Antworten an das Skript:

```sh
python3 crunchyroll_mapping.py episode.json series.json seasons.json \
  episodes-page-1.json episodes-page-2.json --output mapping.json
```

Eine Eingabedatei kann eine einzelne Antwort oder eine Antwort mit einem
`data`-Objekt beziehungsweise `data`-Array enthalten. Mehrere Episodenseiten
werden zusammengeführt; doppelte IDs werden kombiniert. Die Ausgabe enthält
`series`, `seasons` und `episodes` sowie gefundene `next_cursors`. Episoden
enthalten, soweit in den Antworten vorhanden, unter anderem IDs, Titel,
Reihenfolge, Veröffentlichungsdatum, Laufzeit und Sprachversionen.

Führe die Tests aus mit:

```sh
python3 -m unittest discover -s tests
```
