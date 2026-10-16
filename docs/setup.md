# Einrichtung: GitHub, Codex und Cloudflare für den Persisch-Vokabeltrainer

Stand: 16. Oktober 2026. Ergänzung zu „Persisch-Vokabeltrainer-Konzept.md“. Diese Anleitung beschreibt die Einrichtung; Accounts, Verbindungen und Ressourcen wurden damit noch nicht erstellt.

## Der empfohlene Weg

Verwende Codex Cloud für die Entwicklung und Cloudflare Workers Builds für das automatische Deployment. Du hast bereits GitHub. Neu benötigst du zunächst einen Cloudflare-Account und ein privates Projekt-Repository.

Die Ersteinrichtung machst du am besten im Browser am Computer. Danach kannst du auch vom Smartphone aus mit einer veröffentlichten Codex-Umgebung arbeiten. [1]

| Verbindung | Zweck | Einrichtung |
|---|---|---|
| Codex → GitHub | Code lesen, bearbeiten und Änderungen zur Übernahme bereitstellen | GitHub bei der Codex-Umgebung verbinden |
| Cloudflare → GitHub | Den übernommenen Code automatisch bauen und deployen | Cloudflare Workers & Pages GitHub-App autorisieren |
| Codex → Cloudflare | Ressourcen, Datenbank und Deployments verwalten bzw. prüfen | Begrenzter API-Token als Network Secret |
| ChatGPT → deine Anwendung | Vokabeln lesen und Lernergebnisse speichern | Später den eigenen MCP-Endpunkt mit eigener Anmeldung verbinden |

Diese Zugänge sind unabhängig. Ein GitHub-Login in Cloudflare verleiht Codex keine Cloudflare-Rechte. Das Infrastruktur-Token darf nicht der Zugangsschlüssel für deinen Vokabeltutor werden.

## 1. Privates GitHub-Repository anlegen — du

1. Öffne https://github.com/new.
2. Name als Vorschlag: persisch-trainer.
3. Wähle Private und lege eine README an, damit ein erster Commit existiert.
4. Lade das Konzept und diese Anleitung hoch, beispielsweise nach docs/konzept.md und docs/setup.md.
5. Nutze main als vorgesehenen Produktionsbranch.

Das Repository enthält später Code, Konfiguration, Migrationen und Testdaten. Passwörter, Tokens und echte Datenbankexporte gehören nicht hinein. Codex soll eine passende .gitignore für lokale Secrets, Caches und Datenbankdateien anlegen.

Erfolgskriterium: Du kannst das private Repository und beide Dokumente auf GitHub öffnen.

## 2. Cloudflare-Account erstellen — du

1. Öffne https://dash.cloudflare.com/sign-up.
2. Registriere dich und bestätige deine E-Mail-Adresse.
3. Aktiviere Zwei-Faktor-Authentifizierung und bewahre Wiederherstellungscodes auf.
4. Öffne im Dashboard Workers & Pages.
5. Notiere die Account ID aus den Account-Details; sie ist eine Kennung, kein Passwort.

Für die erste Worker-Adresse genügt eine workers.dev-Subdomain. Du musst dafür keine Domain kaufen, umziehen oder Nameserver ändern. [3] Eine spätere eigene Domain für Verwaltung oder Authentifizierung ist eine separate Entscheidung.

Starte mit den für deinen Account verfügbaren kostenlosen Möglichkeiten. Prüfe angezeigte Preise vor einer kostenpflichtigen Aktivierung. Diese Anleitung verspricht keinen dauerhaft kostenlosen Gesamtbetrieb.

Erfolgskriterium: Du erreichst das Cloudflare-Dashboard und hast die richtige Account ID.

## 3. Codex mit GitHub verbinden — du

In der aktuellen Codex-Cloud-Oberfläche:

1. Öffne ChatGPT im Web oder in der Desktop-App.
2. Wähle Work in → Cloud → Select environment → Create environment. Alternativ: Settings → Codex Cloud → Environments.
3. Verbinde GitHub, wenn du dazu aufgefordert wirst.
4. Gib für dieses Projekt das Repository persisch-trainer frei und wähle es aus.
5. Starte die Vorbereitung mit Get started.
6. Lass Codex Abhängigkeiten und Werkzeuge vorbereiten; prüfe den Bericht und veröffentliche die Umgebung mit Publish. [1]

Projektvorgabe: Die Umgebung soll privat bleiben und Python, einen geeigneten Paketmanager, Node.js sowie eine gepinnte Wrangler-Version bereitstellen. Node.js ist hier ein Werkzeug für Cloudflare; deine Fachlogik bleibt Python.

Erfolgskriterium: Eine neue Codex-Aufgabe kann das Repository lesen, eine Datei bearbeiten und lokale Tests ausführen. Ein Zugriff zum Durchsuchen von GitHub allein beweist noch keinen funktionierenden Entwicklungsworkflow mit Änderungen und Pull Requests.

## 4. Cloudflare-Token für Codex erstellen — du

Öffne https://dash.cloudflare.com/profile/api-tokens und wähle Create Token. Erstelle einen eigenen User-Token, beispielsweise mit dem Namen codex-persisch-trainer. Die Vorlage Edit Cloudflare Workers kann als Ausgangspunkt dienen; prüfe und reduziere ihre Rechte. Beschränke die Account Resources auf deinen neuen Account. Der Token wird nur einmal vollständig angezeigt. [5]

Vorgesehene Berechtigungen:

| Berechtigung | Warum |
|---|---|
| Account → Workers Scripts → Edit | Worker anlegen/ändern und deployen |
| Account → D1 → Edit | Datenbanken, Schema und Testdaten verwalten |
| Account → Account Settings → Read | Bei Bedarf Account-Informationen auflösen |
| Account → Workers Builds Configuration → Edit | Nur falls Codex auch die Git-Build-Konfiguration per API verwalten soll |

D1-Schreibrechte sind ausdrücklich erforderlich, wenn Codex Datenbanken über die API verändern soll. [6] Die letzte Berechtigung ist für die manuelle Git-Verknüpfung im Dashboard nicht erforderlich. Die Builds-API verlangt aktuell einen User-Token; deshalb wird hier dieser Typ verwendet. [7]

Keinen Global API Key verwenden. DNS-, Zonen-, Abrechnungs- oder Tokenverwaltungsrechte sind für den beschriebenen Start nicht vorgesehen. Fehlende Rechte anhand einer konkreten Operation ergänzen, nicht pauschal Vollzugriff geben.

Beachte: Eine Begrenzung auf einen Account ist nicht automatisch eine Begrenzung auf einen einzelnen Worker oder eine einzelne Datenbank. Für spätere zusätzliche Projekte die verfügbaren feineren Berechtigungen prüfen.

Erfolgskriterium: Du hast einen separaten widerrufbaren Token für dieses Projekt sicher abgelegt.

## 5. Cloudflare-Zugang in Codex hinterlegen — du, anschließend Codex

Öffne die Konfiguration der Codex-Cloud-Umgebung und trage ein:

| Ort | Name | Wert |
|---|---|---|
| Environment variables | CLOUDFLARE_ACCOUNT_ID | Deine Account ID |
| Network secrets | CLOUDFLARE_API_TOKEN | Der neue Token |
| Allowed domains dieses Secrets | — | api.cloudflare.com |

Network Secrets stellen Programmen einen Platzhalter bereit; der Proxy setzt das echte Geheimnis bei passenden HTTPS-Anfragen ein. Die Ersetzung gilt für Port 443 während Setup und Aufgaben. Das Programm erhält dabei nicht einfach den Rohwert. [2]

Wrangler unterstützt die Variablennamen CLOUDFLARE_API_TOKEN und CLOUDFLARE_ACCOUNT_ID. [8] Dass die konkrete Wrangler-Version mit dem Network-Secret-Mechanismus funktioniert, soll Codex praktisch testen. Ein API-Zugriff ist ebenfalls möglich.

Lass Codex zuerst Tokenstatus und Account-Zugriff prüfen und die D1-Datenbanken auflisten. Niemals den Token ausgeben lassen. Ein gültiger Token allein beweist noch nicht die benötigten Ressourcenrechte.

Netzwerkzugriff auf Paketquellen und die Cloudflare-API zulassen. Später kommt der genaue Hostname deines Workers für Funktionstests hinzu. Speichere bzw. veröffentliche die Änderungen an der Umgebung und prüfe sie in einer neuen Aufgabe. [2]

Falls deine Oberfläche nur das ältere Codex Cloud zeigt: Dort sind Secrets laut Legacy-Dokumentation nur während des Setup-Skripts verfügbar. Sie dürfen nicht heimlich in Dateien kopiert werden, um diese Beschränkung zu umgehen. Verwende dann einen unterstützten aktuellen Zugang, den lokalen Weg aus Abschnitt 10 oder beschränke Codex zunächst auf Code und Deployment über Git. [9]

## 6. Erstes Projektgerüst und Datenbanken — Codex

Jetzt kann Codex den technischen Teil übernehmen. Gib ihm diesen Auftrag:

> Lies docs/konzept.md und docs/setup.md. Bereite zuerst einen minimalen Python-Worker mit D1-Zugriff und einem einfachen Health-Endpunkt vor. Prüfe den Cloudflare-Zugang, ohne Secrets auszugeben. Lege die benötigten Ressourcen im angegebenen Account an, beginne mit einer getrennten Entwicklungsdatenbank und verwende ausschließlich Testdaten. Pinne funktionierende Versionen. Dokumentiere die tatsächlichen Befehle für Setup, Tests, Migrationen und Deployment. Prüfe danach die MCP-Kompatibilität in der echten Workers-Laufzeit. Zeige mir konkrete fehlende Rechte oder notwendige Kontoentscheidungen. Aktiviere keinen kostenpflichtigen Tarif ohne meine ausdrückliche Zustimmung.

Vorgeschlagene Ressourcennamen:

| Ressource | Name |
|---|---|
| Entwicklungs-Worker | persisch-trainer-dev |
| Entwicklungsdatenbank | persisch-trainer-dev |
| Produktions-Worker, später | persisch-trainer |
| Produktionsdatenbank, später | persisch-trainer-prod |
| D1-Binding im Worker | DB |

Codex soll die echten Datenbank-IDs in der Workers-Konfiguration referenzieren und Migrationen versionieren. D1 benötigt beim Zugriff über das Worker-Binding kein zusätzliches Datenbankpasswort in deiner Anwendung. Der Infrastruktur-Token bleibt außerhalb der Worker-Laufzeit.

Lokale D1-Tests und Cloudflare-Daten sind getrennte Umgebungen. Migrationen müssen ihr Ziel ausdrücklich benennen. [10]

Erfolgskriterium: Ein Test-Worker kann einen Testdatensatz schreiben und nach einem neuen Aufruf wieder lesen.

## 7. Cloudflare mit GitHub verbinden — du

Erst verbinden, wenn das Repository ein funktionierendes Projektgerüst und eine Workers-Konfiguration enthält.

Für einen bereits angelegten Worker:

1. Cloudflare → Workers & Pages → deinen Worker auswählen.
2. Settings → Builds → Connect.
3. GitHub auswählen und die Cloudflare Workers and Pages-App autorisieren.
4. Only select repositories wählen und persisch-trainer freigeben.
5. Repository und den passenden Branch auswählen.
6. Die von Codex getesteten Build- und Deploy-Befehle eintragen.

Alternativ beginnt ein neuer Worker unter Create application → GitHub. Der Workername muss zur Konfiguration im Repository passen. [3][4]

Cloudflare erzeugt für Workers Builds standardmäßig einen eigenen Deployment-Token oder erlaubt die Auswahl eines vorhandenen Tokens. Dieser Build-Zugang ist unabhängig vom Codex-Token. Führt der Build auch D1-Migrationen aus, benötigt der dafür verwendete Zugang zusätzlich die passenden D1-Rechte. [11]

Wichtig: Build-Secrets und Worker-Laufzeit-Secrets sind verschiedene Einstellungen. Ein Secret im Build ist nicht automatisch für die laufende Anwendung verfügbar. [11]

Empfehlung für dieses Projekt: Codex arbeitet auf Branches und erstellt Pull Requests. Nach Übernahme nach main läuft das Produktionsdeployment. Entwicklungs- und Preview-Deployments verwenden niemals versehentlich die Produktionsdatenbank. Zunächst reichen gezielte Deployments des Entwicklungs-Workers.

Erfolgskriterium: Eine übernommene kleine Änderung löst einen erfolgreichen Build aus; bestehende Testdaten bleiben erhalten.

## 8. Anmeldung der Anwendung und ChatGPT-Verbindung — später gemeinsam

Das Infrastruktur-Setup ermöglicht die Entwicklung. Für echtes Lernen fehlt dann noch die im Konzept vorgesehene private Anmeldung:

1. Codex schlägt einen konkret kompatiblen OAuth/OIDC-Aufbau für den MCP-Endpunkt vor.
2. Falls dafür ein weiteres Konto nötig ist, registrierst du dich beim gewählten Anbieter.
3. Codex nennt die exakten Callback-URLs, Client-Konfiguration und Secret-Namen.
4. Du trägst die Geheimnisse in die vorgesehene Secret-Verwaltung ein.
5. Zugriff auf deine verifizierte Identität beschränken.
6. Eigenen MCP-Endpunkt in ChatGPT verbinden und anmelden.
7. Eine Vokabel lesen, Ergebnis speichern und in einer neuen Unterhaltung erneut prüfen.
8. Den Test zusätzlich im tatsächlich verwendeten Sprachmodus durchführen.

Diese Anbieterentscheidung ist noch offen; das Konzept hat bisher keinen fertigen Authentifizierungsdienst festgelegt. Deshalb jetzt keine zufälligen OAuth-Accounts oder Client-Secrets anlegen.

Die Möglichkeit, einen eigenen MCP-Server mit schreibenden Tools zu verbinden, vor größerem Ausbau im tatsächlichen ChatGPT-Konto prüfen. Ein funktionierender Codex-Zugang beweist diese Berechtigung nicht. Cloudflare-API-Token niemals in den MCP-Verbindungsdialog als Tutor-Zugang eintragen.

## 9. Was du zuerst wirklich erledigen musst

- [ ] Privates Repository persisch-trainer mit README und beiden Dokumenten anlegen.
- [ ] Cloudflare-Account erstellen, E-Mail bestätigen und 2FA aktivieren.
- [ ] Cloudflare Account ID notieren.
- [ ] Private Codex-Cloud-Umgebung mit dem Repository verbinden.
- [ ] Begrenzten Cloudflare-Token erzeugen.
- [ ] Account ID und Token an den vorgesehenen Stellen hinterlegen.
- [ ] Codex den Auftrag aus Abschnitt 6 geben.
- [ ] Nach dem ersten funktionierenden Gerüst Cloudflare mit GitHub verbinden.
- [ ] MCP-Anmeldung und Sprachtest anschließend durchführen.

Du musst weder einen Linux-Server aufsetzen noch PostgreSQL installieren oder Kubernetes einrichten. Für diese Architektur brauchst du zunächst auch keinen eigenen OpenAI-API-Schlüssel.

## 10. Alternative: Codex lokal auf deinem Computer

Wenn du lieber Codex CLI oder eine lokale IDE-Integration verwendest, klonst du das private Repository auf deinen Computer und öffnest dort das Projekt. GitHub-Zugriff erfolgt über deine lokale Git-Anmeldung. Für Pull Requests kann eine angemeldete GitHub CLI hilfreich sein.

Für Cloudflare kannst du Wrangler interaktiv anmelden, beispielsweise mit npx wrangler login, und den Zugriff mit npx wrangler whoami prüfen. Codex braucht dann die Erlaubnis, die betreffenden Befehle und Netzwerkaufrufe lokal auszuführen. Dieser Login gilt für die lokale Umgebung und wird nicht automatisch nach Codex Cloud übertragen.

Die GitHub-Verbindung von Cloudflare Workers Builds bleibt gleich. Nur der Entwicklungsort wechselt. Nutze entweder den Cloud-Weg oder den lokalen Weg als Hauptablauf; beides gleichzeitig ist für den Einstieg unnötig.

## Quellen

[1] Codex Cloud: https://learn.chatgpt.com/docs/cloud
[2] Aktuelle Cloud-Umgebungen und Network Secrets: https://learn.chatgpt.com/docs/environments/cloud-environments
[3] Workers Builds: https://developers.cloudflare.com/workers/ci-cd/builds/
[4] Cloudflare-GitHub-Integration: https://developers.cloudflare.com/workers/ci-cd/builds/git-integration/github-integration/
[5] Cloudflare-API-Token erstellen: https://developers.cloudflare.com/fundamentals/api/get-started/create-token/
[6] D1-Token und Datenbankzugriff: https://developers.cloudflare.com/d1/tutorials/import-to-d1-with-rest-api/
[7] Workers Builds API: https://developers.cloudflare.com/workers/ci-cd/builds/api-reference/
[8] Wrangler-Umgebungsvariablen: https://developers.cloudflare.com/workers/wrangler/system-environment-variables/
[9] Legacy-Codex-Umgebungen: https://learn.chatgpt.com/docs/environments/cloud-environment
[10] Lokale D1-Entwicklung: https://developers.cloudflare.com/d1/best-practices/local-development/
[11] Workers-Build-Konfiguration: https://developers.cloudflare.com/workers/ci-cd/builds/configuration/

Menübezeichnungen und verfügbare Funktionen können je nach Konto variieren. Die Plattformangaben wurden am 16. Oktober 2026 geprüft; die tatsächliche Einrichtung und Berechtigungsprüfung stehen noch aus.

