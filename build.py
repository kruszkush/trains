#!/usr/bin/env python3
"""Buduje dane dla strony "Przejażdżki" z rozkładu GTFS.

Wybiera wszystkie kursy zatrzymujące się na stacjach początkowych (domyślnie
Sucha Beskidzka Zamek i Sucha Beskidzka; każda to osobna zakładka na stronie), zapisuje ich pełne listy postojów oraz dni kursowania
na najbliższe N dni i wkleja to jako JSON do index.html (plik z szablonu).

Użycie:
  python3 build.py                      # pobiera https://mkuran.pl/gtfs/polish_trains.zip
  python3 build.py --gtfs plik.zip      # lokalny plik GTFS
"""
import argparse
import csv
import io
import json
import re
import sys
import time
import urllib.request
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

GTFS_URL = "https://mkuran.pl/gtfs/polish_trains.zip"
USER_AGENT = "przejazdzki (+https://github.com/kruszkush/trains)"
HERE = Path(__file__).resolve().parent


def download(url, tries=4):
    for i in range(tries):
        try:
            # mkuran.pl odrzuca domyślny User-Agent Pythona (403)
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            return urllib.request.urlopen(req, timeout=180).read()
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            print(f"Błąd pobierania ({e}), ponawiam", file=sys.stderr)
            time.sleep(60 * (i + 1))


def read_csv(zf, name):
    with zf.open(name) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))


def to_min(t):
    if not t:
        return None
    h, m, *_ = t.split(":")
    return int(h) * 60 + int(m)


def active_dates(zf, start, days):
    """service_id -> zbiór dat (YYYYMMDD) w oknie [start, start+days)."""
    window = [start + timedelta(d) for d in range(days)]
    wset = {d.strftime("%Y%m%d") for d in window}
    out = {}
    names = set(zf.namelist())
    wd = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if "calendar.txt" in names:
        for r in read_csv(zf, "calendar.txt"):
            s = out.setdefault(r["service_id"], set())
            for d in window:
                ds = d.strftime("%Y%m%d")
                if r["start_date"] <= ds <= r["end_date"] and r[wd[d.weekday()]] == "1":
                    s.add(ds)
    if "calendar_dates.txt" in names:
        for r in read_csv(zf, "calendar_dates.txt"):
            if r["date"] not in wset:
                continue
            s = out.setdefault(r["service_id"], set())
            if r["exception_type"] == "1":
                s.add(r["date"])
            else:
                s.discard(r["date"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gtfs", help="lokalny plik GTFS .zip (domyślnie pobierany)")
    ap.add_argument("--origin", action="append",
                    help="stacja początkowa (można podać kilka razy)")
    ap.add_argument("--days", type=int, default=21)
    ap.add_argument("--out", default=str(HERE / "index.html"))
    ap.add_argument("--sample", help="napis ostrzegający, że dane są przykładowe")
    ap.add_argument("--codes", help="station_codes.json z kodami stacji dla linków do Bilkomu")
    ap.add_argument("--codes-debug", help="zapisz dopasowane kody stacji do sprawdzenia")
    ap.add_argument("--ids-out", help="zapisz listę trip_id (dla live.py)")
    ap.add_argument("--standalone", action="store_true",
                    help="pełny dokument HTML dla GitHub Pages (manifest, tryb offline, ostrzeżenie o starych danych)")
    args = ap.parse_args()
    origins = args.origin or ["Sucha Beskidzka Zamek", "Sucha Beskidzka"]

    if args.gtfs:
        data = Path(args.gtfs).read_bytes()
    else:
        print("Pobieram", GTFS_URL, file=sys.stderr)
        data = download(GTFS_URL)
    zf = zipfile.ZipFile(io.BytesIO(data))

    tz = ZoneInfo("Europe/Warsaw")
    # dzień wcześniej, żeby łapać kursy po północy z poprzedniej doby
    start = datetime.now(tz).date() - timedelta(days=1)

    # stacje: przystanki/perony łączymy w stację nadrzędną
    stops = {r["stop_id"]: r for r in read_csv(zf, "stops.txt")}

    def station_of(sid):
        r = stops[sid]
        p = r.get("parent_station") or ""
        return p if p in stops else sid

    def clean_name(n):
        return re.sub(r"\s+", " ", n).strip()

    origin_groups = []
    for name in origins:
        norm = name.casefold()
        g = {station_of(s) for s, r in stops.items()
             if clean_name(r["stop_name"]).casefold() == norm}
        if not g:
            sys.exit(f"Nie znaleziono stacji {name!r} w stops.txt")
        origin_groups.append(g)
    origin_stations = set().union(*origin_groups)

    # 1. przebieg: które kursy zatrzymują się na stacji początkowej
    hit = set()
    for r in read_csv(zf, "stop_times.txt"):
        if station_of(r["stop_id"]) in origin_stations:
            hit.add(r["trip_id"])

    # 2. przebieg: pełne listy postojów tych kursów
    st = {}
    for r in read_csv(zf, "stop_times.txt"):
        if r["trip_id"] in hit:
            st.setdefault(r["trip_id"], []).append(r)

    trips = {r["trip_id"]: r for r in read_csv(zf, "trips.txt") if r["trip_id"] in hit}
    routes = {r["route_id"]: r for r in read_csv(zf, "routes.txt")}
    agencies = {r.get("agency_id", ""): r["agency_name"] for r in read_csv(zf, "agency.txt")}
    services = active_dates(zf, start, args.days + 1)

    station_idx, station_names = {}, []

    def sidx(sid):
        k = station_of(sid)
        if k not in station_idx:
            station_idx[k] = len(station_names)
            station_names.append(clean_name(stops[k]["stop_name"]))
        return station_idx[k]

    origin_idx = [sidx(sorted(g)[0]) for g in origin_groups]

    out_trips, days = [], {}
    for tid, trip in trips.items():
        dates = services.get(trip["service_id"], set())
        if not dates:
            continue
        route = routes.get(trip["route_id"], {})
        agency = agencies.get(route.get("agency_id", ""), "") or next(iter(agencies.values()), "")
        rows = sorted(st[tid], key=lambda r: int(r["stop_sequence"]))
        seq = []
        for r in rows:
            arr = to_min(r["arrival_time"]) if r["arrival_time"] else to_min(r["departure_time"])
            dep = to_min(r["departure_time"]) if r["departure_time"] else arr
            # flagi: 1 = nie można wsiąść, 2 = nie można wysiąść
            fl = (1 if r.get("pickup_type") == "1" else 0) | (2 if r.get("drop_off_type") == "1" else 0)
            seq.append([sidx(r["stop_id"]), arr, dep, fl, int(r["stop_sequence"])])
        i = len(out_trips)
        out_trips.append({
            "i": tid,
            "c": route.get("route_short_name") or route.get("route_long_name", ""),
            "l": route.get("route_long_name", ""),
            "n": trip.get("trip_short_name", ""),
            "h": trip.get("trip_headsign", ""),
            "a": agency,
            "b": 1 if route.get("route_type") == "3" else 0,
            "s": seq,
        })
        for d in dates:
            days.setdefault(f"{d[:4]}-{d[4:6]}-{d[6:]}", []).append(i)

    bk = [None] * len(station_names)
    if args.codes and Path(args.codes).exists():
        from math import cos, radians, hypot
        codes = json.loads(Path(args.codes).read_text(encoding="utf-8"))
        dbg = []
        for k, i in station_idx.items():
            lat, lon = float(stops[k]["stop_lat"]), float(stops[k]["stop_lon"])
            name = station_names[i].casefold()
            best = None
            for c in codes:
                d = hypot((c["lat"] - lat) * 111.2, (c["lon"] - lon) * 111.2 * cos(radians(lat)))
                if d > 1.5:
                    continue
                score = (c["n"].casefold() != name, d)   # najpierw zgodna nazwa, potem odległość
                if best is None or score < best[0]:
                    best = (score, c)
            if best:
                bk[i] = best[1]["c"]
            dbg.append(f'{station_names[i]}\t{bk[i] or "-"}\t{best[1]["n"] + " " + best[1]["src"] + " %.2f km" % best[0][1] if best else ""}')
        if args.codes_debug:
            Path(args.codes_debug).write_text("\n".join(sorted(dbg)) + "\n", encoding="utf-8")
        print(f"kody Bilkomu dla {sum(1 for x in bk if x)}/{len(bk)} stacji", file=sys.stderr)

    payload = {
        "bk": bk,
        "origins": origin_idx,
        "generated": datetime.now(tz).strftime("%Y-%m-%d %H:%M"),
        "stations": station_names,
        "trips": out_trips,
        "days": dict(sorted(days.items())),
    }
    if args.sample:
        payload["sample"] = args.sample
    tpl = (HERE / "template.html").read_text(encoding="utf-8")
    js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = tpl.replace("/*__DATA__*/null", js)
    if args.standalone:
        html = (HERE / "static" / "head.html").read_text(encoding="utf-8") + html \
            + (HERE / "static" / "tail.html").read_text(encoding="utf-8")
    Path(args.out).write_text(html, encoding="utf-8")
    if args.ids_out:
        Path(args.ids_out).write_text("\n".join(t["i"] for t in out_trips) + "\n", encoding="utf-8")
    print(f"{len(out_trips)} kursów, {len(station_names)} stacji, {len(days)} dni -> {args.out}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
