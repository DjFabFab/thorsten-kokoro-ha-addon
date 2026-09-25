# Thorsten Kokoro HA Add-on

Deutsche Sprachausgabe mit Thorstens Stimme für Home Assistant, auf Basis des Kokoro Modells. Das Add-on läuft komplett lokal auf der CPU, ohne Cloud und ohne Grafikchip.

## Überblick

- **Stimme:** Thorsten, deutsch (de)
- **HTTP Server:** Port 8000, `GET /health` und `POST /tts`
- **Wyoming Server:** Port 10200 für die Home Assistant Assist Pipeline
- **Plattform:** CPU-only, amd64 und aarch64
- **Modell:** Thorsten-Voice/Kokoro, ein Feinschliff des Kokoro-82M Modells
- **Voraussetzung:** Home Assistant 2023.8 oder neuer

Das Add-on startet zwei Prozesse: den HTTP Server und die Wyoming Bridge. Beide laden das Modell separat in den Arbeitsspeicher. Der RAM Verbrauch liegt dadurch bei etwa 700 MB bis 1 GB.

## Installation

### Repository hinzufügen

1. In Home Assistant zu **Einstellungen → Add-ons → Add-on Store** gehen.
2. Oben rechts das Menü öffnen und **Repositories** wählen.
3. Diese URL hinzufügen:

   ```
    https://github.com/DjFabFab/thorsten-kokoro-ha-addon
   ```

4. Mit **Hinzufügen** bestätigen. Das Add-on **Thorsten Kokoro** erscheint danach im Store.

### Add-on installieren und starten

1. Im Add-on Store **Thorsten Kokoro** öffnen.
2. Auf **Installieren** klicken. Das Image ist etwa 2,7 GB groß, der Download dauert etwas. Standardmäßig wird das vorgebaute Image `ghcr.io/djfabfab/thorsten-kokoro-ha-addon` in der zur Add-on Version passenden Tag Version installiert, siehe vorgebautes Image.
3. Optional die Optionen anpassen, siehe Konfiguration.
4. Auf **Starten** klicken. Beim ersten Start lädt das Add-on das Modell von Hugging Face, das kann einige Minuten dauern.

## Vorgebautes Image

Das Add-on nutzt das vorgebaute Image auf GHCR:

- Paket: `https://github.com/DjFabFab/thorsten-kokoro-ha-addon/pkgs/container/thorsten-kokoro-ha-addon`
- Image: `ghcr.io/djfabfab/thorsten-kokoro-ha-addon:<VERSION>`

Tag und Versions Regel: der Image Tag entspricht immer der Add-on Version aus `thorsten_kokoro/config.yaml` (`version`). Ein Release Tag `v<VERSION>` baut und veröffentlicht `ghcr.io/djfabfab/thorsten-kokoro-ha-addon:<VERSION>`. Es gibt bewusst kein `latest` als Quelle für Home Assistant.

Lokaler Build als Rückfall: enthält `thorsten_kokoro/Dockerfile`, daher baut Home Assistant das Image bei Bedarf lokal. Ohne `image:` Eintrag oder ohne Zugriff auf GHCR wird automatisch lokal gebaut.

### Optionen

| Option | Beschreibung |
| --- | --- |
| KOKORO_EPOCH | Feinschliff-Epoche des Modells. Werte 1 bis 10, Standard 5. |
| SPEED | Sprechgeschwindigkeit. Werte 0.1 bis 2.0, Standard 1.0. |
| HF_REPO_ID | Hugging Face Repository mit Modell und Stimme. Standard Thorsten-Voice/Kokoro. |

## Wyoming Integration

So bindest du das Add-on in den Sprachassistenten ein:

1. In Home Assistant zu **Einstellungen → Geräte und Dienste** gehen.
2. **Integration hinzufügen** und **Wyoming** auswählen.
3. Als Host die Adresse deiner Home Assistant Instanz eintragen, zum Beispiel `homeassistant.local` oder die lokale IP.
4. Als Port **10200** eintragen.
5. Die Integration findet das Add-on und zeigt die Stimme **Thorsten** an.

Das Add-on bietet Wyoming Auto-Discovery an. Nach dem Start schlägt Home Assistant die Integration oft direkt vor.

Danach unter **Einstellungen → Sprachassistenten** eine Pipeline anlegen oder bearbeiten und bei **Text-to-Speech** die Stimme **Thorsten** wählen.

## HTTP Nutzung

Der HTTP Server läuft auf Port 8000 und bietet zwei Endpunkte.

### Health Check

```
curl -s http://localhost:8000/health
```

Die Antwort ist `{"status":"ok"}`.

### Text zu Sprache

```
curl -s -X POST http://localhost:8000/tts -H "Content-Type: application/json" -d '{"text":"Hallo, hier spricht Thorsten."}' --output hallo.wav
```

Die Antwort ist eine WAV Datei mit 24 kHz und Mono. Mit `--output hallo.wav` wird sie direkt gespeichert.

## Epoch Tabelle

Das Modell wurde in mehreren Epochen feingeschliffen. Epoche 5 ist der Standard und die empfohlene Wahl. Andere Epochen laden eigene Dateien.

| Epoch | Modell Datei | Stimme Datei |
| --- | --- | --- |
| 1 | model_ep1.pth | voices/thorsten_ep1.pt |
| 2 | model_ep2.pth | voices/thorsten_ep2.pt |
| 3 | model_ep3.pth | voices/thorsten_ep3.pt |
| 4 | model_ep4.pth | voices/thorsten_ep4.pt |
| 5 (Standard) | model.pth | voices/thorsten.pt |
| 6 | model_ep6.pth | voices/thorsten_ep6.pt |
| 7 | model_ep7.pth | voices/thorsten_ep7.pt |
| 8 | model_ep8.pth | voices/thorsten_ep8.pt |
| 9 | model_ep9.pth | voices/thorsten_ep9.pt |
| 10 | model_ep10.pth | voices/thorsten_ep10.pt |

## Konfiguration

| Option | Wertebereich | Standard | Beschreibung |
| --- | --- | --- | --- |
| KOKORO_EPOCH | 1 bis 10 | 5 | Feinschliff-Epoche des Modells |
| SPEED | 0.1 bis 2.0 | 1.0 | Sprechgeschwindigkeit |
| HF_REPO_ID | Text | Thorsten-Voice/Kokoro | Hugging Face Repository |

## Ports

| Port | Protokoll | Zweck |
| --- | --- | --- |
| 8000 | HTTP | TTS Server, `GET /health` und `POST /tts` |
| 10200 | Wyoming | Sprachassistent Integration |

## RAM Hinweis

Das Add-on startet zwei Prozesse: den HTTP Server und die Wyoming Bridge. Beide laden das Modell separat in den Arbeitsspeicher. Rechne mit etwa 700 MB bis 1 GB RAM. Auf einem Raspberry Pi 4 mit 4 GB ist das machbar, aber spürbar.

## Bekannte Limits

- **Bindestrich-Komposita:** Wörter mit Bindestrich wie "E-Mail" kann die Phonemisierung nicht immer korrekt verarbeiten.
- **Lange Sätze:** Texte werden an Satzgrenzen in Abschnitte von etwa 300 Zeichen gesplittet. Einzelne sehr lange Sätze werden an Wortgrenzen geteilt.
- **Kurzes ü (ʏ):** Der deutsche Phonemisierer kann das Symbol ʏ für das kurze ü erzeugen. Das Kokoro Vokabular kennt nur das lange ü (y). Das Add-on ersetzt ʏ automatisch durch y, damit Wörter wie "Brücke" korrekt gesprochen werden.
- **Umlaute:** Ä, Ö, Ü und ß funktionieren normal.

## Links

- [Thorsten-Voice/Kokoro auf Hugging Face](https://huggingface.co/Thorsten-Voice/Kokoro)
- [thorstenvoice/kokoro-tts auf Docker Hub](https://hub.docker.com/r/thorstenvoice/kokoro-tts)
- [Wyoming Integration Dokumentation](https://www.home-assistant.io/integrations/wyoming/)