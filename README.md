# Przejażdżki z Suchej

Strona na telefon z przejażdżkami pociągiem tam i z powrotem z Suchej Beskidzkiej (przystanek Zamek i stacja): odjazd, stacja nawrotu, czas czekania, powrót i przewoźnik.

- Rozkład: otwarte dane PKP PLK, feed GTFS „Polish Trains” z [mkuran.pl](https://mkuran.pl/gtfs/).
- Odświeżanie: GitHub Actions 3 razy dziennie (ok. 4:17, 12:17, 20:17) buduje `index.html` (`build.py` + `template.html`) i publikuje go na gałęzi `gh-pages`.
- Jeśli odświeżanie się nie uda, strona zostaje z poprzednim rozkładem, pokazuje ostrzeżenie, a GitHub wysyła maila o nieudanym zadaniu.
- Opóźnienia: GitHub Actions co ok. 10 min (5:00–24:00) wycina z feedu mkuran.pl kursy ze strony i zapisuje `live.json` na gałęzi `live`; strona pokazuje je tylko, gdy mają mniej niż 25 min.
- Przycisk „Kup tam”: link do Bilkomu z kodami stacji (IBNR/UIC z Wikidanych i OSM, `station_codes.py`), godziną odjazdu i trasą bez przesiadek; dopasowanie w `station_codes.txt` na stronie.
- Działa offline i można ją dodać do ekranu głównego telefonu.

Lokalnie: `python3 build.py --standalone --out site/index.html`.
