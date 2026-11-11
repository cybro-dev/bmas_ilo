# bmas_ilo

Doku-Repo zum **Film „Beifahrersitz" über ilo 7araga** (ROCC Film für BMAS / SGB2.info,
Regie: Lukas Hablitzel). Kein Code — reine Wissensbasis für Vorbereitung, Drehtag und
Schnitt.

**Dieses Repo liest nur Claude.** Lukas liest hier im Normalfall nichts nach, er schickt
Material (Briefings, Mails, Call-Transkripte) in die Session und stellt Fragen. Die Doku
ist das Gedächtnis zwischen den Sessions — sie muss so geschrieben sein, dass eine frische
Session daraus in fünf Minuten wieder sprechfähig ist. Einstieg: `CONTEXT.md`.

## Aufbau

Getrennt danach, **wodurch sich etwas ändert** — damit die Doku nicht verrottet:

| Art | Ändert sich, wenn … | Liegt in |
| --- | --- | --- |
| **Kontext** | selten — Rahmen des Projekts, Wer-ist-wer, Namensfallen | `CONTEXT.md` |
| **Fakten** | die Realität sich ändert (Termine, Orte, Inhalte, Freigaben) | `docs/*.md` |
| **Offene Punkte** | sie beantwortet werden | `docs/offene-punkte.md` |
| **Korrespondenz** | **gar nicht** — Beleg zum Stichtag | `docs/korrespondenz/` |

**Regel:** Eine Information lebt an *genau einer* Stelle. Übersichten verlinken, sie
wiederholen nicht. Erledigte offene Punkte wandern in die zugehörige Fachdatei, nicht in
eine Archivliste.

## Workflow, wenn neues Material kommt

1. **Beleg ablegen:** Mail / Transkript / PDF nach `docs/korrespondenz/` bzw. `anlagen/`,
   Dateiname `JJJJ-MM-TT-absender-thema.md`. Roh-Transkripte unverändert als eigene
   `…-transkript.md` speichern, daneben ein bereinigtes Protokoll. PDFs mit `pdftotext`
   lesen.
2. **Extrahieren:** Was feststeht → Fachdatei. Was unklar ist → `offene-punkte.md`.
   Was den Rahmen betrifft → `CONTEXT.md`.
3. **Index pflegen:** `docs/korrespondenz/README.md` und die Einstiegspunkte in
   `CONTEXT.md`.
4. **Commit und Push** auf den Arbeitsbranch, damit die nächste Session den Stand hat.

**Plex-Server** (Recherche-Material, z. B. Rap La Rue): nur über Tailscale erreichbar,
Key in `TS_AUTH_KEY` — Anleitung in `docs/plex-server.md`.

**To-dos und Zeiterfassung laufen in Lyfe** (Projekt „ilo 7araga (BMAS / ROCC)").
`offene-punkte.md` hält die *inhaltlichen* Fragen und wer sie beantwortet; was Lukas
selbst tun muss, zusätzlich als Lyfe-Task anlegen.

## Konventionen

- **Sprache der Doku: Deutsch. Der Film ist Deutsch.**
- Datumsangaben absolut (`05.11.2026`), nie „übermorgen".
- ⚠️ **Zwei Schäfers, Chris ≠ Christian, Elias = ilo 7araga.** Immer mit Nachnamen bzw.
  eindeutig schreiben — siehe Namensfallen in `CONTEXT.md`.
- **Northeim**, nicht Nordheim. **ilo 7araga** klein geschrieben.
- Unbestätigtes als solches markieren (⚠️ oder „unbestätigt"), nicht als Fakt notieren.
- Im Projekt nie das Wort „Werbung" verwenden — auch intern nicht, damit es nicht
  rausrutscht. Es ist ein **dokumentarischer Film** / eine **Erfolgsgeschichte**.
