# Persisch-Vokabeltrainer

Erstes Entwicklungsgerüst für einen Python-Worker mit Cloudflare D1.
Die Einrichtungsplanung steht in [docs/setup.md](docs/setup.md).

## Status

- Python-Worker `sprachtrainer` mit D1-Binding `DB`.
- Entwicklungsdatenbank `persisch-trainer-dev`; ihre echte ID steht in `wrangler.jsonc`.
- Schema und Lernstand in `migrations/`; Details in [docs/learning.md](docs/learning.md).
- Cloudflare Workers Builds ist mit `avonb/Sprachtrainer`, Branch `work`, verbunden.
- Anmeldung, Lernoberfläche und MCP sind noch nicht implementiert.
- Interne Vokabelverwaltung mit Umschrift, Beispielsätzen, Bewertungsverlauf und Wiederholungsterminen ist vorbereitet.

## Lokale Entwicklung

Voraussetzungen: Node.js 24, Python >=3.12 und uv. Pywrangler installiert zusätzlich
seine Python-/Pyodide-Buildumgebung. Paketquellen einschließlich `index.pyodide.org`
müssen erreichbar sein.

In Codex können schreibbare Cache-Verzeichnisse erforderlich sein:

```sh
export UV_CACHE_DIR=/workspace/.cache/uv
export UV_PYTHON_INSTALL_DIR=/workspace/.cache/uv/python
export XDG_CACHE_HOME=/workspace/.cache
export XDG_CONFIG_HOME=/workspace/.config
export npm_config_cache=/workspace/.cache/npm
cd /workspace/Sprachtrainer
npm ci
uv sync --frozen
npm run db:migrate:local
npm run build
npm run dev
```

Danach in einem zweiten Terminal prüfen:

```sh
curl --fail http://127.0.0.1:8787/health
curl --fail http://127.0.0.1:8787/health/db
```

Erwartet: `status: ok`; der Datenbank-Endpunkt meldet zusätzlich die Anzahl
vorhandener Vokabeln. Die Endpunkte liefern keine Vokabelinhalte und erlauben
keine Schreibzugriffe. Anmeldung, Lernoberfläche und MCP sind noch nicht implementiert.

## Deployment der Entwicklungsumgebung

Cloudflare Workers Builds verwendet Branch `work` mit:

- Build-Befehl: `npm run build`
- Deploy-Befehl: `npm run deploy`

Für ein manuelles Deployment müssen `CLOUDFLARE_API_TOKEN` und
`CLOUDFLARE_ACCOUNT_ID` gesetzt sein. Schemaänderungen vor dem Deployment
explizit auf die Entwicklungsdatenbank anwenden:

```sh
npm run db:migrate:remote
npm run build
npm run deploy
```

`db:migrate:remote` ändert die echte Entwicklungsdatenbank und benötigt D1-Schreibrechte.
Migrationen sind bewusst kein automatischer Teil des Build-Befehls.

Die Endpunkte der Entwicklungsumgebung sind:

- https://sprachtrainer.j-a-von-berg.workers.dev/health
- https://sprachtrainer.j-a-von-berg.workers.dev/health/db

Unter `/` gibt es noch keine Oberfläche; dort liefert der Worker HTTP 404.
Produktionsdatenbank und Produktionsdeployment werden getrennt eingerichtet.
Secrets gehören in die Plattformverwaltung, niemals in dieses Repository.
