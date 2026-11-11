#!/usr/bin/env python3
"""
Läuft AUF DEM PLEX-SERVER (per `tailscale ssh root@plex 'python3 - --apply' < plex_server_tag.py`).
Beschriftet die Serie „Rap La Rue" (Staffel 1, 56 Folgen) in der Plex-Bibliothek „Series":
deutscher Originaltitel aus den eingebetteten Metadaten, Runde/Folge, ★ + Label bei
ilo-7araga-Folgen, Beschreibung mit Datum, ilos Song und YouTube-Link.
Ohne --apply: Probelauf. Vor dem Schreiben Sicherung nach ~/rlr-plex-backup-<zeit>.json.
Zuordnung ilo ↔ Folge: Upload-Datum seiner Songs (docs/rap-la-rue.md).
"""
import json, re, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

PREFS = "/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Preferences.xml"
BASE = "http://127.0.0.1:32400"
SHOW = "Rap La Rue"
APPLY = "--apply" in sys.argv

# E-Nummer -> (Stufe, Text). „sicher" = Song am selben Tag wie die Folge erschienen.
ILO = {
    26: ("sicher", "ilo 7araga tritt in Runde 1 an: „Bisou“ (Song erschien am selben Tag wie diese Folge, 30.07.2023)."),
    36: ("sicher", "ilo 7araga in Runde 2 (Top 40): „Va Bene“ (Song erschien am selben Tag wie diese Folge, 24.09.2023)."),
    44: ("vermutlich", "Am Tag dieser Folge erschien die RLR-Cypher mit ilo 7araga, Avie, Amo, Juu, Omerta075, Moel030 (22.10.2023)."),
    45: ("vermutlich", "Runde 3, Gruppe 3 mit ilo 7araga: „Sabado“ (mit Parda, Moufasa419, Shorty99ine, Black Retriever). Song erschien 11.01.2024, vier Tage nach dieser Folge."),
    46: ("vermutlich", "Runde 3 – ilo 7araga ist mit Gruppe 3 noch im Rennen um die Villa."),
    47: ("vermutlich", "Runde 3 – Entscheidung, wer in die Villa kommt. ilo 7araga kommt ins Finale."),
    48: ("vermutlich", "Finale/Villa – ilo 7araga ist dabei."),
    49: ("vermutlich", "Finale/Villa – „Paff paff“ (Haaland936 x ilo 7araga), Song erschien 22.02.2024, vier Tage nach dieser Folge."),
    50: ("vermutlich", "Finale/Villa – ilo 7araga ist dabei."),
    51: ("vermutlich", "Finale/Villa – „Substanzen“ (Jiyo x Aymen x ilo 7araga), Song erschien 07.03.2024, vier Tage nach dieser Folge."),
    52: ("vermutlich", "Finale/Villa – „Ich lieb ich dich“ (ilo 7araga), Song erschien 14.03.2024, vier Tage nach dieser Folge."),
    53: ("vermutlich", "Finale/Villa – „Luna“ (ilo 7araga), Song erschien 21.03.2024, vier Tage nach dieser Folge."),
    54: ("vermutlich", "Finale/Villa – „Casablanca“ (Aymen x ilo 7araga), Song erschien 28.03.2024, vier Tage nach dieser Folge."),
    55: ("vermutlich", "Finale/Villa – „Ice“ (ilo 7araga), Song erschien 04.04.2024, vier Tage nach dieser Folge."),
    56: ("vermutlich", "Live-Show – vier Tage danach erschien „RLR Connect“ (Brel, ilo 7araga, Amo, Aymen, Haaland936, Kauta). Ob ilo live auftritt: unbestätigt."),
}


def runde(e):
    if e <= 14: return "Bewerbungen", e - 0 - 1 if e > 1 else 0
    if e <= 32: return "R1", e - 14
    if e <= 34: return "BTS", e - 32
    if e <= 44: return "R2", e - 34
    if e <= 47: return "R3", e - 44
    if e <= 55: return "Finale", e - 47
    return "Live", 1


TITEL = {
    1: "Aufruf – Bewerbungsphase startet",
    2: "Bewerbungen 1 – Die ersten Bewerber (mit Juri)",
    3: "Bewerbungen 2 – mit Bobby Vandamme",
    4: "Bewerbungen 3 – mit O.G",
    5: "Bewerbungen 4 – Versteck dein Talent (mit Juri)",
    6: "Bewerbungen 5 – Hör auf die Hater",
    7: "Bewerbungen 6 – Versteck dein Talent",
    8: "Bewerbungen 7 – mit Sugar MMFK",
    9: "Bewerbungen 8 – Ich bin gespannt",
    10: "Bewerbungen 9 – Wer sind die Nächsten (mit Bojan)",
    11: "Bewerbungen 10 – Ich check die nächsten Bewerbungen",
    12: "Bewerbungen 11 – SadiQ zu Gast",
    13: "Bewerbungen 12 – mit Juri",
    14: "Bewerbungen 13 – mit Silva",
    15: "R1·F01 – Der Beginn einer neuen Ära",
    16: "R1·F02 – Hoch & runter",
    17: "R1·F03 – Ich bin da",
    18: "R1·F04 – Die Liga",
    19: "R1·F05 – Nur so gewinnt man",
    20: "R1·F06 – Was habe ich davon",
    21: "R1·F07 – Lächeln & Weinen",
    22: "R1·F08 – Was sagen deine Schuhe über dich",
    23: "R1·F09 – Den Respekt vor dir selbst",
    24: "R1·F10 – Auf dem Schiff",
    25: "R1·F11 – Die Erfahrung",
    26: "R1·F12 – An die Grenze",
    27: "R1·F13 – Jeder Zentimeter",
    28: "R1·F14 – Du bist besser",
    29: "R1·F15 – Beschütze deine Träume",
    30: "R1·F16 – Sei stark",
    31: "R1·F17 – Dämmerung",
    32: "R1·F18 – The End (letzte Folge)",
    33: "Behind the Scenes – Vlog Teil 1",
    34: "Behind the Scenes – Vlog Teil 2",
    35: "R2·F01 – Top 40",
    36: "R2·F02 – Top 40",
    37: "R2·F03 – Top 40",
    38: "R2·F04 – Top 40",
    39: "R2·F05 – Top 40",
    40: "R2·F06 – Top 40",
    41: "R2·F07 – Top 40",
    42: "R2·F08 – Top 40",
    43: "R2·F09 – Top 40",
    44: "R2·F10 – Letzte Folge & Joker",
    45: "R3·F01 – Stress in der Luft (Rumble in the Jungle)",
    46: "R3·F02 – Das Ende dieser Gruppe? (Loyalty over Love)",
    47: "R3·F03 – Wer kommt in die Villa? (Final Destination)",
    48: "Finale 1/8 – Der Kampf um die Zimmer",
    49: "Finale 2/8 – Bring in the Money",
    50: "Finale 3/8 – Der unsichtbare Gast",
    51: "Finale 4/8 – Alle guten Dinge sind 3",
    52: "Finale 5/8 – Desert Storm",
    53: "Finale 6/8 – Amors Pfeil",
    54: "Finale 7/8 – Rotes Licht, grünes Licht",
    55: "Finale 8/8 – Das Ende / Libero",
    56: "Grand Finale – Live-Show",
}

RLABEL = {"Bewerbungen": "Bewerbungs-Stream", "R1": "Runde 1 · Casting", "BTS": "Behind the Scenes",
          "R2": "Runde 2 · Top 40", "R3": "Runde 3 · Gruppen", "Finale": "Runde 4 · Finale (Villa)",
          "Live": "Grand Finale · Live-Show"}


def api(path, method="GET", tok=None):
    sep = "&" if "?" in path else "?"
    req = urllib.request.Request(f"{BASE}{path}{sep}X-Plex-Token={tok}", method=method,
                                 headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        b = r.read()
        return json.loads(b) if b and method == "GET" else None


def main():
    tok = re.search(r'PlexOnlineToken="([^"]+)"', Path(PREFS).read_text()).group(1)
    secs = api("/library/sections", tok=tok)["MediaContainer"]["Directory"]
    sec = next(s for s in secs if s["title"] == "Series")
    shows = api(f"/library/sections/{sec['key']}/all?type=2&title={urllib.parse.quote(SHOW)}", tok=tok)
    show = next(s for s in shows["MediaContainer"]["Metadata"] if s["title"] == SHOW)
    eps = api(f"/library/metadata/{show['ratingKey']}/allLeaves", tok=tok)["MediaContainer"]["Metadata"]
    backup, n = [], 0
    bp = Path.home() / f"rlr-plex-backup-{time.strftime('%Y%m%d-%H%M%S')}.json"
    for ep in sorted(eps, key=lambda x: (x.get("parentIndex", 0), x.get("index", 0))):
        f = ep["Media"][0]["Part"][0]["file"]
        m = re.search(r"S01E(\d{3})", f)
        if not m:
            continue
        e = int(m.group(1))
        tags = json.loads(subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", f],
                                         capture_output=True, text=True).stdout)["format"].get("tags", {})
        r, k = runde(e)
        title = TITEL[e]
        stufe, note = ILO.get(e, ("", ""))
        if stufe == "sicher":
            title = "★ " + title
        elif stufe:
            title = "☆ " + title
        d = tags.get("date", "")
        datum = f"{d[6:8]}.{d[4:6]}.{d[:4]}" if len(d) == 8 else ""
        summary = [f"Rap La Rue · Staffel 1 · {RLABEL[r]}" + (f" · Folge {k}" if r in ("R1", "R2", "R3") else ""),
                   f"Original-Titel: {tags.get('title', '')}", f"Erschienen: {datum} (DelarueTV)"]
        if note:
            summary += ["", f"ilo 7araga ({stufe}): {note}"]
        summary += ["", tags.get("comment", "")]
        labels = ["ilo 7araga"] if stufe == "sicher" else (["ilo 7araga (vermutlich)"] if stufe else [])
        print(f"E{e:03d}  {title}   {labels or ''}")
        backup.append(dict(ratingKey=ep["ratingKey"], title=ep.get("title"), summary=ep.get("summary"),
                           originallyAvailableAt=ep.get("originallyAvailableAt")))
        if not APPLY:
            continue
        bp.write_text(json.dumps(backup, ensure_ascii=False, indent=1))
        q = {"type": 4, "id": ep["ratingKey"], "title.value": title, "title.locked": 1,
             "summary.value": "\n".join(summary), "summary.locked": 1}
        if datum:
            q.update({"originallyAvailableAt.value": f"{d[:4]}-{d[4:6]}-{d[6:]}", "originallyAvailableAt.locked": 1})
        for i, lab in enumerate(labels):
            q[f"label[{i}].tag.tag"] = lab
        if labels:
            q["label.locked"] = 1
        api(f"/library/sections/{sec['key']}/all?" + urllib.parse.urlencode(q), method="PUT", tok=tok)
        n += 1
    if APPLY:
        print(f"\n{n} Folgen aktualisiert. Sicherung: {bp}")
    else:
        print("\nProbelauf – nichts geändert.")


main()
