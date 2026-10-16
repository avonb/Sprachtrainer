# Persisch-Vokabeltrainer

Erstes Entwicklungsgerüst für einen Python-Worker mit Cloudflare D1.
Die Einrichtungsplanung steht in [docs/setup.md](docs/setup.md).

## Status

- Wrangler 4.151.1 und Python-Abhängigkeiten sind über Lockdateien festgelegt.
- Die lokale D1-Migration und das persistente Schreiben/Lesen einer Testvokabel wurden geprüft.
- Worker-Build und HTTP-Endpunkte sind noch nicht verifiziert: Der Zugriff auf
  `https://index.pyodide.org` ist in der aktuellen Codex-Umgebung gesperrt.
- Es wurden noch keine Cloudflare-Ressourcen, Builds oder GitHub-Verknüpfungen angelegt.
- Die Datenbank-ID in `wrangler.jsonc` ist ein Platzhalter für lokale Entwicklung.
  Vor einem Deployment muss sie durch die echte ID einer Entwicklungsdatenbank ersetzt werden.

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

## Cloudflare und automatisches Hosting: noch offen

1. Cloudflare-Zugang in diesem Chat verfügbar machen und Account bestimmen.
2. Entwicklungsdatenbank `persisch-trainer-dev` anlegen und ihre echte ID eintragen.
3. Build und HTTP-/D1-Funktionstests erfolgreich abschließen.
4. Migration explizit auf die Entwicklungsdatenbank anwenden und Entwicklungs-Worker deployen.
5. Code zu GitHub übertragen; derzeit existiert nur ein lokaler Branch `work`.
6. Cloudflare Workers Builds mit `avonb/Sprachtrainer` und dem vorgesehenen Branch
   verbinden. Die GitHub-App-Autorisierung kann eine Anmeldung im Browser erfordern.
7. Build-/Deploy-Befehle in der echten Builds-Umgebung testen, bevor automatische
   Deployments aktiviert werden. Dort müssen Node.js und uv verfügbar sein.

Produktionsdatenbank und Produktionsdeployment werden getrennt eingerichtet.
Secrets gehören in die Plattformverwaltung, niemals in dieses Repository.
