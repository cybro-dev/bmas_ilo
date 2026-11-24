# Rap La Rue → Plex

Füllt die Plex-Metadaten der heruntergeladenen Rap-La-Rue-Folgen auf und sucht, in welchen
Folgen ilo 7araga vorkommt. Hintergrund und Ergebnisse: [docs/rap-la-rue.md](../../docs/rap-la-rue.md).

> **Stand 11.11.2026: erledigt mit `plex_server_tag.py`.** Das Skript lief per
> `tailscale ssh root@plex 'python3 - --apply' < plex_server_tag.py` direkt auf dem Server
> (Zugang: [docs/plex-server.md](../../docs/plex-server.md)). Es nimmt die Titel und Daten aus den
> Dateien selbst und ordnet ilo über die Upload-Daten seiner Songs zu, ganz ohne YouTube.
> Sicherung der alten Plex-Werte: `/root/rlr-plex-backup-20261111-114912.json` auf dem Server.
>
> `rlr_plex.py` (unten) ist der ursprüngliche Weg über YouTube-Untertitel. Er geht erst wieder,
> wenn YouTube die Server-IP nicht mehr blockt, und arbeitet mit anderer Nummerierung
> (ohne Bewerbungs-Streams).

## Dateien

| Datei | Inhalt |
| --- | --- |
| `plex_server_tag.py` | **benutzt:** beschriftet die 56 Folgen auf dem Server (Titel, ★/☆, Beschreibung, Datum, Labels) |
| `rlr_plex.py` | Alternative über YouTube-Untertitel (`scan`, `plex`, `rename`) |
| `rlr_episoden.json` | 122 Videos, alle von **DelarueTV**: die 107 aus „RAP LA RUE – ALLE FOLGEN" plus 13 Bewerbungs-Streams und 2 Behind-the-Scenes-Vlogs (Specials). YouTube-ID, Staffel, Runde, Folge, sauberer Titel |
| `rlr_scan.json`, `rlr_ilo_report.md` | entstehen beim `scan` |

## Ablauf

```bash
pip install -U yt-dlp plexapi

# 1) ilo suchen (nur Staffel 1, ca. 40 Folgen, ein paar Minuten)
python3 rlr_plex.py scan --staffel 1
python3 rlr_plex.py scan --staffel 0    # Specials: Bewerbungs-Streams (ist Elias' Bewerbung dabei?), Cypher, Trailer
#    blockt YouTube: --cookies-from-browser firefox   (oder chrome)
#    → rlr_ilo_report.md ansehen: Treffer mit Zeitstempel-Links

# 2) Plex: erst Probelauf, dann schreiben
export PLEX_URL=http://<plex-ip>:32400
export PLEX_TOKEN=<token>      # Plex Web → Medium → … → Medieninfo → XML anzeigen → X-Plex-Token in der URL
python3 rlr_plex.py plex --library "<Name der Mediathek>"
python3 rlr_plex.py plex --library "<Name der Mediathek>" --apply

# 3) optional: Dateien nach Serienschema umbenennen (dann als TV-Serie in Plex)
python3 rlr_plex.py rename --dir "/pfad/zu/den/Folgen"
python3 rlr_plex.py rename --dir "/pfad/zu/den/Folgen" --apply
```

## Was in Plex landet

- **Titel** `R1·F03 – I'm Here`, mit ★ davor, wenn ilo per Untertitel/Beschreibung gefunden wurde
- **Sortiertitel** `RLR S01E003` → richtige Reihenfolge in jeder Ansicht
- **Beschreibung**: Staffel · Runde · Folge, ilos Song(s) in dieser Runde, Zeitstempel der
  Fundstellen, YouTube-Kapitel, Link, YouTube-Beschreibung
- **Datum**: YouTube-Upload-Datum (nach `scan`)
- **Labels**: `Rap La Rue`, `Staffel 1`, `ilo 7araga` bzw. `ilo 7araga (wahrscheinlich)`
- **Sammlungen**: eine pro Runde (`RLR Staffel 1 · Runde 1` …) und `★ ilo 7araga`

Zuordnung Plex ↔ YouTube: über die YouTube-ID im Dateinamen (yt-dlp-Standard
`Titel [ID].mp4`), sonst über den Titel. Nicht Zuordenbares wird am Ende aufgelistet.

Specials (Season 0): Trailer, RLR Cypher, Bewerbungs-Streams, Behind the Scenes. Staffeln sind durchnummeriert
(Staffel 1 = E01–E40), die Runde steht im Titel.
