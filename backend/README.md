# Backend — SALESFLY

API FastAPI per SALESFLY (CRM per agenti di commercio plurimandatari). Deploy su Railway (Railpack), servizio con Root Directory `/backend`.

## Dipendenze: pyproject.toml + uv.lock

Dal 2026-08-28 le dipendenze sono gestite con [uv](https://docs.astral.sh/uv/), non più con `requirements.txt`:

- **`pyproject.toml`** — elenca i vincoli di versione voluti (`dependencies` per il runtime, `[dependency-groups] dev` per pytest/black/isort/flake8/mypy, non installati in produzione).
- **`uv.lock`** — il lockfile: congela l'intero grafo delle dipendenze risolte (versioni esatte + hash), committato nel repo. **Va sempre committato insieme a `pyproject.toml`** quando cambia — è quello che garantisce che ogni deploy installi esattamente le stesse versioni.
- **`.python-version`** — pin della versione Python (attualmente 3.12), letta sia da `uv` in locale sia da Railway (Railpack) in produzione.

### Aggiungere o aggiornare una dipendenza

```bash
uv add nome-pacchetto           # aggiunge e blocca subito una nuova dipendenza
uv add --group dev nome-pacchetto   # stessa cosa, ma solo per lo sviluppo (non va in produzione)
uv lock --upgrade-package nome-pacchetto   # aggiorna una dipendenza già presente all'ultima versione compatibile
uv lock                          # rigenera il lockfile dopo una modifica manuale di pyproject.toml
```

Ognuno di questi comandi aggiorna `uv.lock` in automatico — committa sempre `pyproject.toml` + `uv.lock` insieme.

### Ambiente locale

```bash
uv sync          # crea/aggiorna .venv secondo il lockfile
uv run pytest    # esegue la suite di test nell'ambiente sincronizzato
uv run python -m uvicorn server:app --reload
```

Se `uv` non è installato: `pip install uv`.

### Note

- Il backend gira come script (`uvicorn server:app`), non come pacchetto installabile — per questo `pyproject.toml` ha `[tool.uv] package = false` e non serve una sezione `[build-system]`.
- Railway (Railpack) rileva `pyproject.toml`+`uv.lock`+`.python-version` in automatico, nessun build command custom necessario.
- Dettagli sulla migrazione da `requirements.txt`: vedi il commit `5fc4ef7`.
