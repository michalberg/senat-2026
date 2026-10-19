# Senát 2026 – kolik stály kampaně

Statický web s výsledky senátních voleb 2026 a analýzou financování kampaní:
výdaje kandidátů z transparentních volebních účtů, seznamy dárců a zprávy ÚDHPSH.

**Web:** https://michalberg.github.io/senat-2026/

## Struktura

- `docs/` – web (GitHub Pages): `index.html`, `app.js`, `app.css`, `data.json`
- `scripts/` – stahování a zpracování dat
  - `parse_ucty.py` – registr volebních účtů ÚDHPSH → `data/ucty.json`
  - `fetch_fio.py`, `fetch_kb.py`, `fetch_csas.py`, `fetch_rb.py`, `fetch_moneta.py` – pohyby na účtech → `data/raw/ucty/tx/`
  - `parse_darci.py` – seznamy dárců → `data/darci.json`
  - `build.py` – klasifikace transakcí a přiřazení k obvodům → `data/model.json`
  - `analyze.py` – výpočty → `docs/data.json`
- `config/ucty_map.json` – účet → volební strana, `config/prirazeni.json` – ruční opravy přiřazení, `config/anomalie.json` – ručně ověřené anomálie

Přegenerování: `./rebuild.sh` (s `--fetch` znovu stáhne účty).

## Zdroje

- ČSÚ, otevřená data SE 2026: https://volby.gov.cz/opendata/se2026/se2026_opendata.htm
- ÚDHPSH: seznamy dárců, registr volebních účtů, zprávy https://zpravy.udh.gov.cz/zpravy/s2026
- Transparentní účty Fio, KB, ČS, RB, Moneta (skripty) a ČSOB, UniCredit (chráněné proti robotům –
  staženo ručně přes prohlížeč do `data/raw/ucty/browser/`, převod `scripts/convert_browser.py`). Stav k 19. 10. 2026.

Vizuální styl a barvy stran podle [povolebni-analyza](https://github.com/michalberg/povolebni-analyza).
