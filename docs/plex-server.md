# Plex-Server: Zugang und was dort für dieses Projekt liegt

Stand: **11.11.2026**. Lukas' Plex läuft auf einem eigenen Linux-Rechner zu Hause und ist
für Cloud-Sessions **nur über Tailscale** erreichbar. Recherche-Material zum Film (Rap La Rue,
ilos Musikvideos) liegt dort.

## Zugang aus einer Cloud-Session

Der Tailscale-Auth-Key steckt in der Umgebungsvariable **`TS_AUTH_KEY`** (nie ausgeben,
nie committen). Tailscale ist im Container nicht vorinstalliert:

```bash
# 1) Tailscale installieren (statische Binaries, pkgs.tailscale.com ist erreichbar)
V=$(curl -sS 'https://pkgs.tailscale.com/stable/?mode=json' | python3 -c "import json,sys;print(json.load(sys.stdin)['Tarballs']['amd64'])")
curl -sSL "https://pkgs.tailscale.com/stable/$V" | tar xz -C /tmp && cp /tmp/tailscale_*_amd64/tailscale* /usr/local/bin/

# 2) Daemon im Userspace-Modus (kein TUN im Container) + ins Tailnet
mkdir -p /var/lib/tailscale /var/run/tailscale
nohup tailscaled --tun=userspace-networking --state=/var/lib/tailscale/tailscaled.state \
  --socket=/var/run/tailscale/tailscaled.sock \
  --socks5-server=localhost:1055 --outbound-http-proxy-listen=localhost:1056 > /tmp/tailscaled.log 2>&1 &
sleep 3 && tailscale up --authkey="$TS_AUTH_KEY" --hostname=claude-cloud-session
tailscale status | grep -v claude-cloud      # → plex 100.111.211.102

# 3) SSH (Tailscale SSH, als root) – braucht den openssh-client
apt-get install -y openssh-client
tailscale ssh root@plex 'hostname'
```

**Fallen:**
- `curl` kommt in dieser Umgebung **nicht** an den lokalen Tailscale-Proxy (Fehler „Couldn't
  connect … after 0 ms"), und Ziele im Bereich 100.x landen sonst beim Egress-Proxy der
  Umgebung (403 `private_dest_ip`). **Am einfachsten alles per `tailscale ssh` auf dem
  Server erledigen**, dort mit `curl http://127.0.0.1:32400/…`. Von hier aus geht HTTP
  nur mit Python über `http://127.0.0.1:1056` als Proxy.
- `tailscale ssh` nimmt keine `-o`-Optionen.
- Jede Session meldet sich als neues Gerät an (viele alte `claude-cloud-*` im Tailnet).
  Aufräumen in der Tailscale-Admin-Konsole oder einen *ephemeral* Key verwenden.

## Der Server

| | |
| --- | --- |
| Tailscale-Name / IP | `plex` / `100.111.211.102` |
| System | Ubuntu 26.04, Plex Media Server 1.43.5 (systemd `plexmediaserver`) |
| Plex-Token | in `/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Preferences.xml`, Attribut `PlexOnlineToken` — auf dem Server auslesen, nicht ausgeben |
| Medien | `/Volumes/Lukas Films` (5,5 TB), `/Volumes/Lukas Hablitzel 05` (7,3 TB) |
| Lukas' Home | `/home/lukashablitzel` — dort die Download-Skripte und -Listen |
| YouTube-Downloads | `yt-dlp` mit `deno` und bgutil-PO-Token-Provider unter `/usr/local/bin`; als `lukashablitzel` ausführen |

Plex-Bibliotheken: **„Series"** (key 4, `…/Series/`), **„Musik"** (Musikvideos über
`GlobalMusicVideoPath` = `…/Music Videos/`).

## Rap La Rue auf dem Server (geladen 08.11.2026)

| Was | Ordner | Liste (ID ⇥ Dateiname) |
| --- | --- | --- |
| **Rap La Rue, Staffel 1** — 56 Folgen DelarueTV: E001–E014 Bewerbungs-Streams, E015–E032 Runde 1, E033–E034 Behind the Scenes, E035–E044 Runde 2, E045–E047 Runde 3, E048–E055 Finale, E056 Live-Show | `Series/Rap La Rue/Season 01/` | `~/folgen.tsv` |
| **Rap La Rue – Musikvideos** (194, alle Songs der Staffel 1) | `Series/Rap La Rue - Musikvideos/Season 01/` | `~/musikvideos.tsv` |
| **ilo 7araga Musikvideos** (17, außerhalb der Show) | `Music Videos/` | `~/ilo.tsv` |

Download-Skript: `~/raplarue-s1.sh` (Log `~/raplarue-s1.log`) — wartet bei YouTube-Block
15 min und versucht es erneut, scannt danach die Bibliothek.

Die Nummerierung auf dem Server (E001–E056) weicht von der in
`werkzeuge/rap-la-rue-plex/rlr_episoden.json` ab (dort ohne Bewerbungs-Streams). Maßgeblich
für Plex ist der Server.
