import uuid
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

# Fuso orario di riferimento per "che giorno/mese è oggi" dal punto di vista
# dell'utente (agenti italiani). Gestisce CET/CEST automaticamente tramite il
# database IANA (pacchetto tzdata, già una dipendenza del progetto).
LOCAL_TZ = ZoneInfo("Europe/Rome")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_local() -> datetime:
    """'Adesso' convertito in ora italiana — da usare SOLO per stabilire
    confini di calendario ("oggi", "questo mese"), mai per salvare timestamp
    (che restano sempre in UTC puro tramite now_iso()).

    Perché serve: datetime.now(timezone.utc) da solo fa sì che "oggi" per il
    backend resti indietro di un giorno per 1-2 ore ogni notte (tra la
    mezzanotte italiana e il momento in cui anche l'orologio UTC gira),
    perché l'Italia è avanti rispetto a UTC di 1h (CET) o 2h (CEST)."""
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ)


def local_date_str(iso_ts: Optional[str]) -> str:
    """Converte un timestamp UTC salvato (es. appointment.start,
    offer.created_at) nella sua data di calendario in ora italiana, formato
    'YYYY-MM-DD'. Da usare al posto di iso_ts[:10] ogni volta che il
    risultato va confrontato con un "oggi"/"questo mese" ottenuto da
    now_local() — affettare direttamente la stringa UTC produce la data
    sbagliata per la stessa finestra di 1-2 ore vicino alla mezzanotte
    italiana descritta in now_local(). Ritorna stringa vuota se il timestamp
    manca o non è nel formato atteso, per restare compatibile con l'uso
    precedente di iso_ts[:10] su valori assenti."""
    if not iso_ts:
        return ""
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(LOCAL_TZ).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return ""


def local_month_str(iso_ts: Optional[str]) -> str:
    """Come local_date_str, ma restituisce solo 'YYYY-MM'."""
    return local_date_str(iso_ts)[:7]


def local_month_start_utc_iso() -> str:
    """Istante UTC (ISO) della mezzanotte del primo giorno del mese corrente
    in ora italiana — da usare in una query '>= created_at' (sempre salvato
    in UTC puro tramite now_iso()) per contare/filtrare eventi 'di questo
    mese' direttamente nel database, senza scaricare tutta la cronologia."""
    start_local = now_local().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start_local.astimezone(timezone.utc).isoformat()


def local_wallclock_to_utc_iso(local_str: str) -> str:
    """Converte una data/ora 'a muro' in ora italiana, senza fuso orario
    esplicito (es. "2026-07-25T10:00:00", il formato che il tool
    dell'assistente AI riceve dal modello) nel corrispondente istante UTC, in
    formato ISO. Se la stringa ha già un fuso orario esplicito, viene
    rispettato e convertito in UTC senza reinterpretarlo come ora italiana.

    Perché serve: senza questa conversione, gli appuntamenti creati dall'AI
    finiscono salvati come stringa "naive" (nessun offset), mentre quelli
    creati dal form web sono veri istanti UTC — lo stesso campo `start`
    conterrebbe due rappresentazioni diverse e incompatibili, rompendo ogni
    confronto "è nel futuro?"/"è oggi?" fatto altrove nel codice."""
    dt = datetime.fromisoformat(local_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL_TZ)
    return dt.astimezone(timezone.utc).isoformat()


def gen_id() -> str:
    return str(uuid.uuid4())


def clean(doc: Optional[dict]) -> Optional[dict]:
    if doc is None:
        return None
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc
