# trains

Statyczna strona na telefon „Przejażdżki z Suchej”: przejazdy pociągiem tam i z powrotem z Suchej Beskidzkiej. Publikowana na GitHub Pages: https://kruszkush.github.io/trains/ (repo publiczne). Opis funkcji: `README.md`.

## Uruchomienie lokalne
`python3 build.py --standalone --out site/index.html` (pobiera GTFS z https://mkuran.pl/gtfs/polish_trains.zip albo `--gtfs plik.zip`). `site/` jest w .gitignore. Kody stacji: `python3 station_codes.py station_codes.json` (opcjonalne; bez nich przyciski „Kup” są ukryte). Tylko biblioteka standardowa Pythona.

## Wdrożenie (GitHub Actions, brak lokalnego zadania)
- `.github/workflows/build.yml`: 3x dziennie (cron `17 2,10,18`) i przy pushu na main buduje stronę i publikuje na gałąź `gh-pages` (`force_orphan`, jeden commit). Zapisuje też `trip_ids.txt`.
- `.github/workflows/live.yml`: co 10 min uruchamia `live.py`, wycina z feedu opóźnień kursy ze strony i publikuje `live.json` na gałąź `live`.
- Oba workflowy przy każdym przebiegu re-włączają harmonogram przez API (GitHub wyłącza go po 60 dniach bez aktywności). Nie usuwaj tego kroku.

## Mapa plików
- `build.py`: GTFS -> dane JSON wklejone do `template.html`; `static/` (head/tail, `sw.js`, manifest, ikony) tworzy PWA działające offline.
- `live.py`: feed `updates.json` mkuran.pl (ok. 27 MB, bez CORS, więc nie z przeglądarki).
- `station_codes.py`: kody IBNR/UIC z Wikidanych i OSM dla linków do Bilkomu; dopasowanie po położeniu.

## Pułapki
- mkuran.pl odrzuca domyślny User-Agent Pythona (403); zostaw własny UA z linkiem do repo.
- Przy błędzie pobierania `live.py` nie zwraca błędu (bez maili co 10 min), a strona sama pokazuje, że dane są stare.
