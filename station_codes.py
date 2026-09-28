#!/usr/bin/env python3
"""Pobiera 7-cyfrowe kody stacji (IBNR/UIC, np. 5100065), których używa Bilkom w linkach.

Rozkład PLK ma własne numery stacji, więc kody bierzemy z Wikidanych (IBNR, P954)
i z OpenStreetMap (uic_ref), a potem build.py dopasowuje je po położeniu.

Użycie: python3 station_codes.py station_codes.json
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "przejazdzki (+https://github.com/kruszkush/trains)"

SPARQL = """
SELECT ?name ?code ?coord WHERE {
  ?s wdt:P17 wd:Q36; wdt:P954 ?code; wdt:P625 ?coord.
  ?s rdfs:label ?name. FILTER(LANG(?name) = "pl")
}"""

OVERPASS = """
[out:json][timeout:120];
area["ISO3166-1"="PL"][admin_level=2]->.pl;
(node["railway"~"station|halt"]["uic_ref"](area.pl);
 node["public_transport"="station"]["uic_ref"](area.pl););
out;"""


def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=180))


def main():
    out = []
    try:
        r = get("https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(SPARQL))
        for b in r["results"]["bindings"]:
            lon, lat = b["coord"]["value"].removeprefix("Point(").rstrip(")").split()
            code = b["code"]["value"].strip()
            if code.isdigit() and len(code) == 7 and code.startswith("51"):
                out.append({"n": b["name"]["value"], "c": code, "lat": float(lat), "lon": float(lon), "src": "wd"})
    except Exception as e:  # noqa: BLE001
        print(f"Wikidane: {e}", file=sys.stderr)
    try:
        r = get("https://overpass-api.de/api/interpreter", urllib.parse.urlencode({"data": OVERPASS}).encode())
        for el in r["elements"]:
            code = el["tags"].get("uic_ref", "").strip()
            if code.isdigit() and len(code) == 7 and code.startswith("51"):
                out.append({"n": el["tags"].get("name", ""), "c": code, "lat": el["lat"], "lon": el["lon"], "src": "osm"})
    except Exception as e:  # noqa: BLE001
        print(f"OSM: {e}", file=sys.stderr)
    if not out:
        sys.exit("Brak kodów stacji z obu źródeł")
    Path(sys.argv[1]).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"{len(out)} kodów stacji", file=sys.stderr)


if __name__ == "__main__":
    main()
