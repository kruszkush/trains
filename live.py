#!/usr/bin/env python3
"""Wycina z feedu opóźnień mkuran.pl tylko kursy, które są na stronie.

Feed ma ~27 MB i nie pozwala na pobranie z przeglądarki (brak CORS), więc
GitHub Actions co kilka minut zapisuje z niego mały live.json:

  {"ts": "<czas feedu>", "fetched": "<czas pobrania>",
   "u": {"<trip_id>|<YYYY-MM-DD>": {"c": 1?, "s": {"<stop_sequence>": [przyjazd, odjazd, odwołany]}}}}

przyjazd/odjazd to minuty od północy dnia kursu (jak w rozkładzie na stronie).

Użycie: python3 live.py trip_ids.txt live.json
"""
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

URL = "https://mkuran.pl/gtfs/polish_trains/updates.json"
USER_AGENT = "przejazdzki (+https://github.com/kruszkush/trains)"
TZ = ZoneInfo("Europe/Warsaw")


def minutes(ts, day):
    if not ts:
        return None
    t = datetime.fromisoformat(ts).astimezone(TZ)
    return round((t - day).total_seconds() / 60)


def main():
    ids = set(Path(sys.argv[1]).read_text(encoding="utf-8").split())
    req = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT})
    try:
        feed = json.load(urllib.request.urlopen(req, timeout=180))
    except Exception as e:  # noqa: BLE001
        # bez maila co 10 minut: zostaje poprzedni live.json, strona sama pokaże, że dane są stare
        print(f"Nie udało się pobrać feedu: {e}", file=sys.stderr)
        return
    out = {}
    for u in feed.get("trip_updates") or []:
        if u["trip_id"] not in ids:
            continue
        day = datetime.fromisoformat(u["start_date"]).replace(tzinfo=TZ)
        e = {}
        if u.get("cancelled"):
            e["c"] = 1
        s = {}
        for x in u.get("stop_times") or []:
            if u.get("detour"):
                break  # przy objeździe stop_sequence nie pasuje do rozkładu
            s[str(x["stop_sequence"])] = [minutes(x.get("arrival"), day),
                                          minutes(x.get("departure"), day),
                                          1 if x.get("cancelled") else 0]
        if s:
            e["s"] = s
        if e:
            out[f'{u["trip_id"]}|{u["start_date"]}'] = e
    Path(sys.argv[2]).write_text(json.dumps({
        "ts": feed.get("timestamp"),
        "fetched": datetime.now(TZ).isoformat(timespec="seconds"),
        "u": out,
    }, separators=(",", ":")), encoding="utf-8")
    print(f"{len(out)} kursów z danymi na żywo, feed z {feed.get('timestamp')}", file=sys.stderr)


if __name__ == "__main__":
    main()
