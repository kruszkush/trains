# Przejażdżki z Suchej

Strona na telefon z przejażdżkami pociągiem tam i z powrotem z Suchej Beskidzkiej (przystanek Zamek i stacja): odjazd, stacja nawrotu, czas czekania, powrót i przewoźnik.

- Rozkład: otwarte dane PKP PLK, feed GTFS „Polish Trains” z [mkuran.pl](https://mkuran.pl/gtfs/).
- Odświeżanie: GitHub Actions codziennie ok. 4:17 buduje `index.html` (`build.py` + `template.html`) i publikuje go na gałęzi `gh-pages`.
- Jeśli odświeżanie się nie uda, strona zostaje z poprzednim rozkładem, pokazuje ostrzeżenie, a GitHub wysyła maila o nieudanym zadaniu.
- Działa offline i można ją dodać do ekranu głównego telefonu.

Lokalnie: `python3 build.py --standalone --out site/index.html`.
