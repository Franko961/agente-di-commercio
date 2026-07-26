"""
Verifica che l'export CSV neutralizzi il "CSV Injection"/"Formula Injection":
un valore testuale libero (nome cliente, nota, ecc.) che inizia con =, +, -,
o @ verrebbe interpretato come formula da Excel/Google Sheets quando il file
esportato viene aperto — con rischio di esecuzione di codice o esfiltrazione
dati sulla macchina di chi lo apre, che potrebbe non essere la stessa
persona che ha inserito quel dato (es. l'export girato al proprio mandante).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_csv_export_injection.py -v
"""
import sys
import csv
import io
import asyncio

import pytest

sys.path.insert(0, ".")

from services.export_service import csv_response, _sanitize_csv_cell


def _rows_from_response(response):
    async def _collect():
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
        return chunks
    chunks = asyncio.run(_collect())
    text = "".join(chunks).lstrip("\ufeff")
    return list(csv.reader(io.StringIO(text), delimiter=";"))


@pytest.mark.parametrize("payload", [
    "=HYPERLINK(\"http://evil.example/steal\",\"click\")",
    "=cmd|' /C calc'!A0",
    "+1+1",
    "-1+1",
    "@SUM(1,2)",
])
def test_valore_pericoloso_viene_neutralizzato(payload):
    assert _sanitize_csv_cell(payload) == "'" + payload


@pytest.mark.parametrize("payload", [
    "Rossi Srl", "Mario Rossi", "note normali", "", "+39 0123456789",
])
def test_valore_normale_non_viene_alterato_se_non_a_rischio(payload):
    # Nota: "+39 ..." INIZIA con '+', quindi rientra comunque nella
    # sanitizzazione — è un compromesso accettato (vedi test successivo)
    # dato che Excel nasconde comunque l'apostrofo iniziale in visualizzazione.
    result = _sanitize_csv_cell(payload)
    if payload.startswith(("=", "+", "-", "@")):
        assert result == "'" + payload
    else:
        assert result == payload


def test_numeri_non_vengono_toccati():
    """I valori numerici (importi, conteggi) non sono mai a rischio di
    formula injection e non devono essere alterati, nemmeno se negativi."""
    assert _sanitize_csv_cell(-42.5) == -42.5
    assert _sanitize_csv_cell(0) == 0
    assert _sanitize_csv_cell(100) == 100


def test_export_clienti_neutralizza_nome_pericoloso():
    rows = [{"company_name": "=HYPERLINK(\"http://evil.example\")", "notes": "normale"}]
    response = csv_response(rows, ["company_name", "notes"], "test.csv")
    parsed = _rows_from_response(response)
    header, data_row = parsed[0], parsed[1]
    assert data_row[0] == "'=HYPERLINK(\"http://evil.example\")"
    assert data_row[1] == "normale"


def test_export_con_solo_valori_innocui_resta_leggibile():
    rows = [{"company_name": "Rossi Srl", "notes": "cliente storico"}]
    response = csv_response(rows, ["company_name", "notes"], "test.csv")
    parsed = _rows_from_response(response)
    assert parsed[1] == ["Rossi Srl", "cliente storico"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
