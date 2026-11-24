#!/usr/bin/env python3
"""
Rap La Rue -> Plex: Metadaten auffüllen und ilo-7araga-Auftritte finden.

Läuft LOKAL bei Lukas (dort, wo YouTube nicht blockt und der Plex-Server erreichbar ist).
Drei Schritte, jeder einzeln aufrufbar:

  1) scan    – holt pro Folge Beschreibung, Kapitel, Upload-Datum und die deutschen
               Auto-Untertitel von YouTube und sucht darin nach ilo 7araga.
               Ergebnis: rlr_scan.json + rlr_ilo_report.md
  2) plex    – schreibt Titel, Sortiertitel, Beschreibung, Datum, Labels und
               Sammlungen in Plex. Ohne --apply nur Probelauf (zeigt, was passieren würde).
  3) rename  – (optional) benennt die Dateien nach Plex-Serienschema um
               („Rap La Rue/Season 01/Rap La Rue - S01E03 - ….mp4“). Ohne --apply nur Probelauf.

Installation:  pip install -U yt-dlp plexapi
Plex-Zugang:   PLEX_URL=http://192.168.x.x:32400  PLEX_TOKEN=…  (Token: in Plex Web bei einem
               Medium „…“ → „Medieninfo“ → „XML anzeigen“, steht in der URL als X-Plex-Token)

Beispiele:
  python3 rlr_plex.py scan --staffel 1
  python3 rlr_plex.py plex --library "Rap La Rue"            # Probelauf
  python3 rlr_plex.py plex --library "Rap La Rue" --apply
  python3 rlr_plex.py rename --dir "/pfad/zu/Rap La Rue"      # Probelauf
"""
import argparse
import difflib
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EPISODES_FILE = HERE / "rlr_episoden.json"
SCAN_FILE = HERE / "rlr_scan.json"
REPORT_FILE = HERE / "rlr_ilo_report.md"

# Was in Untertiteln/Beschreibungen als Treffer zählt. Auto-Untertitel schreiben Namen
# oft falsch, deshalb großzügig – jeder Treffer muss im Video kurz gegengecheckt werden.
ILO_PATTERNS = [
    (r"7\s*araga|\bharr?aga\b|\bh?ilo\s+(7|sieben|haraga)", "stark"),
    (r"\bilo\b", "mittel"),
    (r"\bhilo\b|\bilow?\b", "schwach"),
]
# ilo 7araga war Teilnehmer der 1. Staffel (Runde 1 bis Finale, siehe docs/rap-la-rue.md).
ILO_ROUNDS_S1 = {1: "Bisou", 2: "Va Bene", 3: "Sabado (Gruppe 3)",
                 4: "Substanzen, Paff paff, Casablanca, RLR Connect, Ich lieb ich dich, Luna, Ice"}

YT = "https://www.youtube.com/watch?v="


# ---------------------------------------------------------------- Daten

def load_episodes():
    eps = json.loads(EPISODES_FILE.read_text(encoding="utf-8"))
    # Plex-Nummern: pro Staffel durchlaufend, Trailer + Cypher als Season 0 (Specials)
    counters, specials = {}, 0
    for e in eps:
        if e["staffel"] == 0 or e["runde"] == 0:
            specials += 1
            e["plex_season"], e["plex_episode"] = 0, specials
        else:
            counters[e["staffel"]] = counters.get(e["staffel"], 0) + 1
            e["plex_season"], e["plex_episode"] = e["staffel"], counters[e["staffel"]]
    return eps


def load_scan():
    if SCAN_FILE.exists():
        return json.loads(SCAN_FILE.read_text(encoding="utf-8"))
    return {}


def label_ilo(e, scan):
    """Gibt (Stufe, Text) zurück: bestätigt / Treffer / wahrscheinlich / –."""
    s = scan.get(e["id"], {})
    hits = s.get("hits", [])
    strong = [h for h in hits if h["stufe"] == "stark"]
    if s.get("in_description"):
        return "bestätigt", "ilo 7araga in der Videobeschreibung genannt"
    if strong:
        return "treffer", f"{len(strong)} starke Untertitel-Treffer"
    if hits:
        return "treffer?", f"{len(hits)} schwache Untertitel-Treffer (prüfen)"
    if e["staffel"] == 1 and e["runde"] in (3, 4):
        return "wahrscheinlich", "ilo war in dieser Runde dabei (Gruppe 3 bzw. Villa/Finale)"
    return "", ""


# ---------------------------------------------------------------- 1) scan

def vtt_to_cues(text):
    cues, cur_t = [], None
    for line in text.splitlines():
        m = re.match(r"(\d+):(\d+):(\d+)\.\d+\s+-->", line)
        if m:
            h, mi, se = map(int, m.groups())
            cur_t = h * 3600 + mi * 60 + se
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if cur_t is not None and line and not line.startswith(("WEBVTT", "Kind:", "Language:")):
            if not cues or cues[-1][1] != line:
                cues.append((cur_t, line))
    return cues


def find_hits(cues):
    hits, last = [], -999
    for t, line in cues:
        for pat, stufe in ILO_PATTERNS:
            if re.search(pat, line, flags=re.I):
                if t - last > 20:                 # Treffer innerhalb 20 s zusammenfassen
                    hits.append(dict(t=t, stufe=stufe, text=line))
                    last = t
                break
    return hits


def cmd_scan(args):
    try:
        import yt_dlp
    except ImportError:
        sys.exit("yt-dlp fehlt: pip install -U yt-dlp")
    eps = [e for e in load_episodes() if args.staffel is None or e["staffel"] == args.staffel]
    scan = load_scan()
    subdir = HERE / "untertitel"
    subdir.mkdir(exist_ok=True)
    opts = dict(skip_download=True, writeautomaticsub=True, writesubtitles=True,
                subtitleslangs=["de", "de-orig", "de.*"], subtitlesformat="vtt",
                outtmpl=str(subdir / "%(id)s.%(ext)s"), quiet=True, no_warnings=True)
    if args.cookies_from_browser:
        opts["cookiesfrombrowser"] = (args.cookies_from_browser,)
    with yt_dlp.YoutubeDL(opts) as ydl:
        for i, e in enumerate(eps, 1):
            if e["id"] in scan and not args.force:
                continue
            tag = f"S{e['staffel']} R{e['runde']} F{e['folge']:02d}"
            print(f"[{i}/{len(eps)}] {tag} {e['id']} …", flush=True)
            try:
                info = ydl.extract_info(YT + e["id"], download=True)
            except Exception as ex:                       # noqa: BLE001
                print(f"   ! übersprungen: {ex}")
                continue
            desc = info.get("description") or ""
            vtts = sorted(subdir.glob(f"{e['id']}*.vtt"))
            cues = vtt_to_cues(vtts[0].read_text(encoding="utf-8", errors="ignore")) if vtts else []
            scan[e["id"]] = dict(
                title=info.get("title"), upload_date=info.get("upload_date"),
                description=desc, chapters=info.get("chapters") or [],
                has_subs=bool(cues), hits=find_hits(cues),
                in_description=bool(re.search(r"7\s*araga", desc, flags=re.I)),
            )
            SCAN_FILE.write_text(json.dumps(scan, ensure_ascii=False, indent=1), encoding="utf-8")
            time.sleep(args.sleep)
    write_report(load_episodes(), scan)
    print(f"\nFertig. Bericht: {REPORT_FILE}")


def write_report(eps, scan):
    out = ["# Rap La Rue – wo kommt ilo 7araga vor?", "",
           "Automatisch erzeugt aus YouTube-Beschreibungen und Auto-Untertiteln. "
           "Auto-Untertitel verhören Namen – jeden Treffer kurz im Video gegenchecken.", "",
           "| Folge | Titel | ilo | Fundstellen |", "| --- | --- | --- | --- |"]
    for e in eps:
        if e["staffel"] != 1:
            continue
        s = scan.get(e["id"], {})
        stufe, _ = label_ilo(e, scan)
        links = ", ".join(f"[{h['t']//60}:{h['t']%60:02d}]({YT}{e['id']}&t={h['t']}s)"
                          for h in s.get("hits", [])[:12])
        if s and not s.get("has_subs"):
            links = links or "keine Untertitel"
        title = e["titel"]
        out.append(f"| S{e['staffel']} R{e['runde']} F{e['folge']:02d} | {title} | {stufe} | {links} |")
    out += ["", "## Kontext der Treffer", ""]
    for e in eps:
        for h in scan.get(e["id"], {}).get("hits", []):
            out.append(f"- **S{e['staffel']} R{e['runde']} F{e['folge']:02d}** "
                       f"{h['t']//60}:{h['t']%60:02d} ({h['stufe']}): „{h['text']}“")
    REPORT_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 2) plex

def norm(s):
    return re.sub(r"[^a-z0-9äöü]", "", (s or "").lower())


def match_items(items, eps, scan):
    """Ordnet Plex-Einträge den Folgen zu: YouTube-ID im Dateinamen > Titelvergleich."""
    by_id = {e["id"]: e for e in eps}
    titles = {}
    for e in eps:
        for t in (e["yt_title"], scan.get(e["id"], {}).get("title")):
            if t:
                titles[norm(t)] = e
    result, unmatched = [], []
    for it in items:
        files = [p.file for m in getattr(it, "media", []) for p in m.parts]
        hay = " ".join(files + [it.title or ""])
        ep = None
        for vid in re.findall(r"[\[(]([A-Za-z0-9_-]{11})[\])]", hay):
            ep = by_id.get(vid) or ep
        if not ep:
            for vid in re.findall(r"(?<![A-Za-z0-9_-])([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])", hay):
                if vid in by_id:
                    ep = by_id[vid]
                    break
        if not ep:
            cand = [norm(it.title)] + [norm(Path(f).stem) for f in files]
            best, score = None, 0.0
            for c in cand:
                for k, e in titles.items():
                    r = difflib.SequenceMatcher(None, c, k).ratio()
                    if r > score:
                        best, score = e, r
            ep = best if score >= 0.85 else None
        (result.append((it, ep)) if ep else unmatched.append((it, files)))
    return result, unmatched


def plex_fields(e, scan):
    s = scan.get(e["id"], {})
    stufe, why = label_ilo(e, scan)
    st = f"Staffel {e['staffel']}" if e["staffel"] else "Specials"
    if e["staffel"] == 0 or e["runde"] == 0:
        title = e["titel"]
    else:
        title = f"R{e['runde']}·F{e['folge']:02d} – {e['titel']}"
    if stufe in ("bestätigt", "treffer"):
        title = "★ " + title
    summary = [f"Rap La Rue · {st} · {e['runde_label']} · Folge {e['folge']}"]
    if e["staffel"] == 1 and e["runde"] in ILO_ROUNDS_S1:
        summary.append(f"ilo 7araga in dieser Runde: {ILO_ROUNDS_S1[e['runde']]}")
    if stufe:
        summary.append(f"ilo: {stufe} – {why}")
    hits = s.get("hits", [])
    if hits:
        summary.append("Fundstellen: " + ", ".join(f"{h['t']//60}:{h['t']%60:02d}" for h in hits[:15]))
    if s.get("chapters"):
        summary.append("Kapitel: " + " · ".join(
            f"{int(c['start_time'])//60}:{int(c['start_time'])%60:02d} {c['title']}" for c in s["chapters"]))
    summary.append(YT + e["id"])
    if s.get("description"):
        summary += ["", s["description"][:1500]]
    labels = ["Rap La Rue", st]
    if stufe in ("bestätigt", "treffer", "treffer?"):
        labels.append("ilo 7araga")
    if stufe == "wahrscheinlich":
        labels.append("ilo 7araga (wahrscheinlich)")
    collections = [f"RLR {st} · {e['runde_label']}"]
    if "ilo 7araga" in labels:
        collections.append("★ ilo 7araga")
    date = s.get("upload_date")
    return dict(
        title=title,
        sort=f"RLR S{e['plex_season']:02d}E{e['plex_episode']:03d}",
        summary="\n".join(summary),
        date=f"{date[:4]}-{date[4:6]}-{date[6:]}" if date else None,
        labels=labels, collections=collections,
    )


def cmd_plex(args):
    try:
        from plexapi.server import PlexServer
    except ImportError:
        sys.exit("plexapi fehlt: pip install -U plexapi")
    url = args.url or os.environ.get("PLEX_URL")
    token = args.token or os.environ.get("PLEX_TOKEN")
    if not (url and token):
        sys.exit("PLEX_URL und PLEX_TOKEN setzen (oder --url/--token).")
    plex = PlexServer(url, token)
    lib = plex.library.section(args.library)
    items = lib.searchEpisodes() if lib.type == "show" else lib.all()
    eps, scan = load_episodes(), load_scan()
    if not scan:
        print("Hinweis: noch kein Scan vorhanden – schreibe Struktur ohne Untertitel-Treffer.\n")
    matched, unmatched = match_items(items, eps, scan)
    print(f"{len(items)} Einträge in „{args.library}“, {len(matched)} zugeordnet, "
          f"{len(unmatched)} nicht zugeordnet.\n")
    for it, e in sorted(matched, key=lambda x: (x[1]["plex_season"], x[1]["plex_episode"])):
        f = plex_fields(e, scan)
        print(f"  {f['sort']}  {f['title']}   [{', '.join(f['labels'][2:]) or '-'}]")
        if not args.apply:
            continue
        it.editTitle(f["title"], locked=True)
        it.editSortTitle(f["sort"], locked=True)
        it.editSummary(f["summary"], locked=True)
        if f["date"]:
            it.editOriginallyAvailable(f["date"], locked=True)
        for lab in f["labels"]:
            try:
                it.addLabel(lab, locked=True)
            except Exception as ex:                       # noqa: BLE001
                print(f"     ! Label nicht möglich ({type(it).__name__}): {ex}")
                break
        for col in f["collections"]:
            try:
                it.addCollection(col, locked=True)
            except Exception as ex:                       # noqa: BLE001
                print(f"     ! Sammlung nicht möglich ({type(it).__name__}): {ex}")
                break
    if unmatched:
        print("\nNicht zugeordnet (Dateiname enthält keine YouTube-ID, Titel nicht eindeutig):")
        for it, files in unmatched:
            print(f"  - {it.title}  {files[:1]}")
    if not args.apply:
        print("\nProbelauf – nichts geändert. Mit --apply schreiben.")


# ---------------------------------------------------------------- 3) rename

def safe(s):
    return re.sub(r'[<>:"/\\|?*]', "", s).strip()[:120]


def cmd_rename(args):
    root = Path(args.dir)
    eps, scan = load_episodes(), load_scan()
    by_id = {e["id"]: e for e in eps}
    moves = []
    for f in root.rglob("*"):
        if f.suffix.lower() not in (".mp4", ".mkv", ".webm", ".m4v", ".mov"):
            continue
        ids = [v for v in re.findall(r"[A-Za-z0-9_-]{11}", f.stem) if v in by_id]
        if not ids:
            print(f"  ? keine YouTube-ID im Dateinamen: {f.name}")
            continue
        e = by_id[ids[-1]]
        fields = plex_fields(e, scan)
        name = (f"Rap La Rue - S{e['plex_season']:02d}E{e['plex_episode']:02d} - "
                f"{safe(fields['title'].lstrip('★ '))} [{e['id']}]{f.suffix}")
        target = root / f"Season {e['plex_season']:02d}" / name
        if f != target:
            moves.append((f, target))
    for src, dst in moves:
        print(f"  {src.relative_to(root)}\n    -> {dst.relative_to(root)}")
        if args.apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                print("     ! Ziel existiert schon, übersprungen")
                continue
            src.rename(dst)
    print(f"\n{len(moves)} Dateien {'umbenannt' if args.apply else 'würden umbenannt (Probelauf)'}.")


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="YouTube-Metadaten + Untertitel holen, ilo suchen")
    s.add_argument("--staffel", type=int, help="nur diese Staffel (ilo: 1)")
    s.add_argument("--sleep", type=float, default=3.0, help="Pause zwischen Videos (Sek.)")
    s.add_argument("--force", action="store_true", help="schon gescannte Folgen neu holen")
    s.add_argument("--cookies-from-browser", help="z. B. firefox oder chrome, falls YouTube blockt")
    p = sub.add_parser("plex", help="Metadaten in Plex schreiben")
    p.add_argument("--library", required=True, help="Name der Plex-Mediathek")
    p.add_argument("--url"), p.add_argument("--token")
    p.add_argument("--apply", action="store_true")
    r = sub.add_parser("rename", help="Dateien nach Plex-Serienschema umbenennen")
    r.add_argument("--dir", required=True)
    r.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    {"scan": cmd_scan, "plex": cmd_plex, "rename": cmd_rename}[a.cmd](a)


if __name__ == "__main__":
    main()
