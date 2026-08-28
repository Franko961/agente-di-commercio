"""
Verifica services/attendance_xlsx_export.py: costruzione del workbook del
cartellino presenze (foglio "Cartellino" a griglia colorata + foglio
"Dettaglio" a righe piatte), usato da attendance_service.export_xlsx.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_attendance_xlsx_export.py -v
"""

import base64
import io
import sys

sys.path.insert(0, ".")

from services.attendance_xlsx_export import build_attendance_workbook

try:
    from PIL import Image as PILImage

    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def _png_data_url(size=(200, 60), color=(255, 90, 0)) -> str:
    img = PILImage.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _find_row(ws, name, max_row=50):
    for r in range(6, max_row):
        if ws.cell(row=r, column=1).value == name:
            return r
    return None


def build(**overrides):
    defaults = dict(
        month="2028-08",
        company_name="CACI SRL",
        company_logo=None,
        ferie_count_mode="calendario",
        leave_requests=[],
        sessions=[],
    )
    defaults.update(overrides)
    return build_attendance_workbook(**defaults)


def test_ha_i_due_fogli_attesi():
    wb = build()
    assert wb.sheetnames == ["Cartellino", "Dettaglio"]


def test_intestazione_cartellino_contiene_i_numeri_dei_giorni():
    wb = build()
    ws = wb["Cartellino"]
    # riga 5 = intestazione: colonna 1 "Dipendente", colonna 2 = giorno 1 ... colonna 32 = giorno 31
    assert ws.cell(row=5, column=1).value == "Dipendente"
    assert ws.cell(row=5, column=2).value == 1
    assert ws.cell(row=5, column=32).value == 31
    assert ws.cell(row=5, column=33).value == "Ore totali"
    assert ws.cell(row=5, column=34).value == "Giorni ferie"


def test_cella_di_un_giorno_di_ferie_ha_il_colore_atteso():
    wb = build(
        leave_requests=[
            {
                "employee_name": "Mario Rossi",
                "type": "ferie",
                "date_from": "2028-08-10",
                "date_to": "2028-08-12",
                "hours": None,
                "note": "",
            },
        ]
    )
    ws = wb["Cartellino"]
    row = _find_row(ws, "Mario Rossi")
    assert row is not None
    cell = ws.cell(row=row, column=1 + 10)  # giorno 10
    assert cell.fill.fgColor.rgb == "FFFF5A00"  # arancione ferie


def test_giorno_escluso_da_ferie_count_mode_festivita_non_ha_fill_ne_entra_nel_totale():
    """14-27 agosto 2028: 2 sabati, 2 domeniche, Ferragosto (15/8, martedì).
    In modalità 'festivita' la domenica e Ferragosto sono esclusi (11
    giorni contati su 14), il sabato resta incluso — stesso identico
    scenario già verificato per leave_request_service._days_in_year e per
    la griglia live in Presenze.jsx."""
    wb = build(
        ferie_count_mode="festivita",
        leave_requests=[
            {
                "employee_name": "Mario Rossi",
                "type": "ferie",
                "date_from": "2028-08-14",
                "date_to": "2028-08-27",
                "hours": None,
                "note": "",
            },
        ],
    )
    ws = wb["Cartellino"]
    row = _find_row(ws, "Mario Rossi")
    ferragosto_cell = ws.cell(row=row, column=1 + 15)  # martedì, festivo
    domenica_cell = ws.cell(row=row, column=1 + 20)  # domenica
    sabato_cell = ws.cell(row=row, column=1 + 19)  # sabato, non festivo
    assert ferragosto_cell.fill.fgColor.rgb in ("00000000", None)
    assert domenica_cell.fill.fgColor.rgb in ("00000000", None)
    assert sabato_cell.fill.fgColor.rgb == "FFFF5A00"

    giorni_ferie = ws.cell(row=row, column=34).value
    assert giorni_ferie == 11


def test_ore_totali_riga_e_la_somma_delle_sessioni_chiuse_del_mese():
    wb = build(
        sessions=[
            {
                "employee_name": "Anna Bianchi",
                "clock_in": "2028-08-03T07:00:00+00:00",
                "clock_out": "2028-08-03T15:00:00+00:00",
                "note": "",
            },
            {
                "employee_name": "Anna Bianchi",
                "clock_in": "2028-08-04T07:00:00+00:00",
                "clock_out": "2028-08-04T11:00:00+00:00",
                "note": "",
            },
        ]
    )
    ws = wb["Cartellino"]
    row = _find_row(ws, "Anna Bianchi")
    assert ws.cell(row=row, column=33).value == 12.0  # 8h + 4h


def test_straordinari_si_somma_alle_ore_ordinarie_non_le_sostituisce():
    """Il caso segnalato: 8 ore ordinarie + 2 di straordinario lo stesso
    giorno devono dare 10, non far sparire le 8 ordinarie dietro il colore
    dello straordinario."""
    wb = build(
        sessions=[
            {
                "employee_name": "Mario Rossi",
                "clock_in": "2028-08-10T07:00:00+00:00",
                "clock_out": "2028-08-10T15:00:00+00:00",
                "note": "",
            },
        ],
        leave_requests=[
            {
                "employee_name": "Mario Rossi",
                "type": "straordinari",
                "date_from": "2028-08-10",
                "date_to": "2028-08-10",
                "hours": 2,
                "note": "",
            },
        ],
    )
    ws = wb["Cartellino"]
    row = _find_row(ws, "Mario Rossi")
    cell = ws.cell(row=row, column=1 + 10)
    assert (
        cell.fill.fgColor.rgb == "FF16A34A"
    )  # verde presente, non il rosa dello straordinario
    assert cell.value == 10.0  # 8 ordinarie + 2 straordinarie, sommate
    assert ws.cell(row=row, column=33).value == 10.0  # Ore totali di riga


def test_straordinari_senza_timbratura_separata_resta_col_proprio_colore():
    """Uno straordinario dichiarato senza una sessione presenze quel
    giorno (nessuna timbratura) mantiene il comportamento di sempre: cella
    del colore proprio dello straordinario, valore le sue sole ore."""
    wb = build(
        leave_requests=[
            {
                "employee_name": "Mario Rossi",
                "type": "straordinari",
                "date_from": "2028-08-10",
                "date_to": "2028-08-10",
                "hours": 2,
                "note": "",
            },
        ]
    )
    ws = wb["Cartellino"]
    row = _find_row(ws, "Mario Rossi")
    cell = ws.cell(row=row, column=1 + 10)
    assert cell.fill.fgColor.rgb == "FFDB2777"  # rosa straordinari
    assert cell.value == 2.0
    assert ws.cell(row=row, column=33).value == 2.0


def test_straordinari_si_somma_ai_totali_anche_se_coincide_con_unassenza():
    """Uno straordinario lo stesso giorno di un'altra assenza/modalità
    (caso raro) continua comunque a sommarsi al totale ore, anche se la
    cella mostra il colore dell'altro tipo."""
    wb = build(
        leave_requests=[
            {
                "employee_name": "Mario Rossi",
                "type": "malattia",
                "date_from": "2028-08-10",
                "date_to": "2028-08-10",
                "hours": None,
                "note": "",
            },
            {
                "employee_name": "Mario Rossi",
                "type": "straordinari",
                "date_from": "2028-08-10",
                "date_to": "2028-08-10",
                "hours": 2,
                "note": "",
            },
        ]
    )
    ws = wb["Cartellino"]
    row = _find_row(ws, "Mario Rossi")
    cell = ws.cell(row=row, column=1 + 10)
    assert cell.fill.fgColor.rgb == "FFDC2626"  # rosso malattia, non sostituito
    assert (
        ws.cell(row=row, column=33).value == 2.0
    )  # le 2h di straordinario restano comunque nel totale


def test_logo_incluso_solo_se_impostato():
    wb_senza = build(company_logo=None)
    assert len(wb_senza["Cartellino"]._images) == 0

    if _PIL_AVAILABLE:
        wb_con = build(company_logo=_png_data_url())
        assert len(wb_con["Cartellino"]._images) == 1


def test_logo_malformato_non_fa_fallire_lexport():
    wb = build(company_logo="data:image/png;base64,questo-non-e-un-png-valido")
    assert wb.sheetnames == ["Cartellino", "Dettaglio"]
    assert len(wb["Cartellino"]._images) == 0


def test_nota_che_inizia_con_carattere_formula_viene_protetta():
    wb = build(
        leave_requests=[
            {
                "employee_name": "Mario Rossi",
                "type": "permesso",
                "date_from": "2028-08-10",
                "date_to": "2028-08-10",
                "hours": 2,
                "note": "=cmd|'/c calc'!A1",
            },
        ]
    )
    ws = wb["Dettaglio"]
    note_values = [ws.cell(row=r, column=8).value for r in range(2, 5)]
    assert any(isinstance(v, str) and v.startswith("'=") for v in note_values)


def test_dettaglio_contiene_gli_orari_locali_delle_sessioni():
    wb = build(
        sessions=[
            {
                "employee_name": "Anna Bianchi",
                "clock_in": "2028-08-03T07:00:00+00:00",
                "clock_out": "2028-08-03T15:00:00+00:00",
                "note": "",
            },
        ]
    )
    ws = wb["Dettaglio"]
    row = [ws.cell(row=2, column=c).value for c in range(1, 9)]
    assert row[0] == "Anna Bianchi"
    assert row[1] == "Presenza"
    assert row[2] == "2028-08-03"
    # 07:00 UTC = 09:00 ora italiana in agosto (CEST, UTC+2)
    assert row[4] == "09:00"
    assert row[5] == "17:00"
    assert row[6] == 8.0
