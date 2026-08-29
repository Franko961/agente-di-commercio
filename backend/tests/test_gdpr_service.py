"""
Test per gdpr_service: esportazione completa dei dati (art. 20 GDPR) e
cancellazione definitiva dell'account (art. 17 GDPR) — non un soft-delete:
verifica che ogni collection user-scoped venga davvero svuotata e che i file
dei documenti vengano rimossi anche da S3, non solo il loro record.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_gdpr_service.py -v
"""

import asyncio
import io
import json
import sys
import zipfile

sys.path.insert(0, ".")

from fastapi import HTTPException

import services.gdpr_service as gdpr_mod
from services.gdpr_service import (
    EXCLUDED_FROM_USER_SCOPED_COLLECTIONS,
    USER_SCOPED_COLLECTIONS,
    GdprService,
)


def run(coro):
    return asyncio.run(coro)


async def _allow_always(*a, **k):
    return True


async def _deny_always(*a, **k):
    return False


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, n):
        return self._docs[:n]


class FakeCollection:
    def __init__(self, name, docs=None):
        self.name = name
        self.docs = list(docs or [])
        self.deleted_many_calls = []
        self.deleted_one_calls = []
        self.inserted = []

    def find(self, query, projection=None):
        user_id = query.get("user_id")
        docs = [
            d for d in self.docs if (user_id is None or d.get("user_id") == user_id)
        ]
        return FakeCursor(docs)

    async def find_one(self, query, projection=None):
        for d in self.docs:
            if all(d.get(k) == v for k, v in query.items()):
                return dict(d)
        return None

    async def delete_many(self, query):
        self.deleted_many_calls.append(query)
        before = len(self.docs)
        self.docs = [d for d in self.docs if d.get("user_id") != query.get("user_id")]
        return type("R", (), {"deleted_count": before - len(self.docs)})()

    async def delete_one(self, query):
        self.deleted_one_calls.append(query)
        # Match generico su tutte le chiavi della query (non solo "id"): la
        # pulizia dei contatori usa "_id", non "id".
        self.docs = [
            d for d in self.docs if not all(d.get(k) == v for k, v in query.items())
        ]

    async def insert_one(self, doc):
        self.inserted.append(doc)


class FakeDb:
    """Supporta sia db.nome_collection sia db['nome_collection'], perché
    gdpr_service usa entrambe le forme (attributo per i nomi noti, subscript
    nel ciclo su USER_SCOPED_COLLECTIONS)."""

    def __init__(self):
        self._collections = {}

    def _get(self, name):
        if name not in self._collections:
            self._collections[name] = FakeCollection(name)
        return self._collections[name]

    def __getattr__(self, name):
        return self._get(name)

    def __getitem__(self, name):
        return self._get(name)


USER = {"id": "u1", "email": "franco@test.it"}


def build_fake_db_with_data():
    fake_db = FakeDb()
    fake_db.users.docs.append(
        {
            "id": "u1",
            "email": "franco@test.it",
            "name": "Franco",
            "password_hash": "hash-segreto",
            "plan": "pro",
        }
    )
    fake_db.clients.docs.append(
        {"id": "c1", "user_id": "u1", "company_name": "Bar Centrale"}
    )
    fake_db.clients.docs.append(
        {"id": "c2", "user_id": "u2", "company_name": "Cliente di un altro utente"}
    )
    fake_db.offers.docs.append({"id": "o1", "user_id": "u1", "total": 500})
    fake_db.documents.docs.append(
        {
            "id": "d1",
            "user_id": "u1",
            "original_filename": "contratto.pdf",
            "storage_path": "path/to/contratto.pdf",
        }
    )
    fake_db.automation_notifications.docs.append(
        {"id": "n1", "user_id": "u1", "title": "Promemoria"}
    )
    fake_db.automation_notifications.docs.append(
        {"id": "n2", "user_id": "u2", "title": "Notifica di un altro utente"}
    )
    fake_db.automation_runs.docs.append(
        {"automation_id": "auto-1", "user_id": "u1", "target_id": "t1", "status": "ok"}
    )
    fake_db.automation_runs.docs.append(
        {"automation_id": "auto-2", "user_id": "u2", "target_id": "t2", "status": "ok"}
    )
    fake_db.demo_requests.docs.append(
        {"id": "dr1", "user_id": "u1", "nome": "Franco", "email": "franco@test.it"}
    )
    fake_db.demo_requests.docs.append(
        {"id": "dr2", "user_id": "u2", "nome": "Altro", "email": "altro@test.it"}
    )
    fake_db.counters.docs.append({"_id": "order_number:u1", "seq": 7})
    fake_db.counters.docs.append({"_id": "order_number:u2", "seq": 3})
    return fake_db


def test_export_include_profilo_e_dati_utente(monkeypatch):
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(
        gdpr_mod,
        "storage_get",
        lambda path: (b"contenuto pdf finto", "application/pdf"),
    )
    service = GdprService()

    zip_bytes = run(service.export_user_data(USER))

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert "dati.json" in names
        assert "documenti/contratto.pdf" in names
        data = json.loads(zf.read("dati.json"))

    assert data["profilo"]["email"] == "franco@test.it"
    assert "password_hash" not in data["profilo"]  # mai esposto nell'export
    assert len(data["clienti"]) == 1
    assert data["clienti"][0]["company_name"] == "Bar Centrale"
    assert len(data["offerte"]) == 1


def test_export_non_include_dati_di_altri_utenti(monkeypatch):
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(gdpr_mod, "storage_get", lambda path: (b"x", "application/pdf"))
    service = GdprService()

    zip_bytes = run(service.export_user_data(USER))
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        data = json.loads(zf.read("dati.json"))

    company_names = [c["company_name"] for c in data["clienti"]]
    assert "Cliente di un altro utente" not in company_names


def test_export_include_richiesta_demo_e_notifiche_automazioni(monkeypatch):
    """demo_requests e automation_notifications sono dati riconducibili
    all'utente (user_id, e per demo_requests anche nome/email) quindi
    vanno inclusi nell'export (art. 20 GDPR), non solo nella cancellazione."""
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(gdpr_mod, "storage_get", lambda path: (b"x", "application/pdf"))
    service = GdprService()

    zip_bytes = run(service.export_user_data(USER))
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        data = json.loads(zf.read("dati.json"))

    assert len(data["richiesta_demo"]) == 1
    assert data["richiesta_demo"][0]["nome"] == "Franco"
    assert len(data["notifiche_automazioni"]) == 1
    assert data["notifiche_automazioni"][0]["title"] == "Promemoria"


def test_export_prosegue_se_un_documento_non_si_trova(monkeypatch):
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "check_and_record", _allow_always)

    def _raise(path):
        raise Exception("file non trovato su S3")

    monkeypatch.setattr(gdpr_mod, "storage_get", _raise)
    service = GdprService()

    zip_bytes = run(service.export_user_data(USER))  # non deve sollevare

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert "dati.json" in zf.namelist()
        assert "documenti/contratto.pdf" not in zf.namelist()


def test_export_neutralizza_un_nome_documento_con_percorso_malevolo(monkeypatch):
    """Un documento il cui campo 'name' contiene separatori di percorso
    (es. impostato via PATCH dopo il caricamento, che a differenza
    dell'upload iniziale non veniva più ripulito) non deve poter far
    scrivere una voce zip fuori dalla cartella 'documenti/' prevista —
    zipfile non protegge da solo da un arcname tipo '../../evil.sh'."""
    fake_db = FakeDb()
    fake_db.users.docs.append(
        {"id": "u1", "email": "franco@test.it", "name": "Franco", "password_hash": "x"}
    )
    fake_db.documents.docs.append(
        {
            "id": "d1",
            "user_id": "u1",
            "name": "../../evil.sh",
            "storage_path": "path/to/evil.sh",
            # Nessun original_filename: il caso realistico è un vecchio
            # documento, o uno il cui original_filename manca per qualche
            # motivo, che ricade sul campo 'name' modificabile dall'utente.
        }
    )
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(
        gdpr_mod, "storage_get", lambda path: (b"contenuto", "application/octet-stream")
    )
    service = GdprService()

    zip_bytes = run(service.export_user_data(USER))

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        # La garanzia reale di sanitize_filename è l'assenza di separatori di
        # percorso (/ e \) — punti letterali residui (es. ".._.._evil.sh")
        # sono innocui, restano un nome file con caratteri insoliti, non un
        # percorso che uno strumento di estrazione possa risalire. Vedi
        # anche test_percorso_relativo_neutralizzato in
        # test_document_upload_security.py per la stessa proprietà.
        assert not any("/" in n.removeprefix("documenti/") or "\\" in n for n in names)
        assert any(n.startswith("documenti/") for n in names)


def test_cancellazione_richiede_password_corretta(monkeypatch):
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(
        gdpr_mod, "verify_password", lambda plain, hashed: plain == "password-giusta"
    )
    service = GdprService()

    try:
        run(service.delete_account(USER, "password-sbagliata"))
        assert False, "doveva sollevare HTTPException"
    except HTTPException as e:
        assert e.status_code == 403
    # Nulla deve essere stato cancellato con la password sbagliata
    assert len(fake_db.clients.docs) == 2


def test_cancellazione_svuota_tutte_le_collection_dellutente(monkeypatch):
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(gdpr_mod, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(gdpr_mod, "storage_delete", lambda path: None)

    class FakeSubscriptionService:
        async def cancel_subscription(self, user):
            return {"ok": True}

    monkeypatch.setattr(gdpr_mod, "subscription_service", FakeSubscriptionService())

    service = GdprService()
    run(service.delete_account(USER, "qualunque"))

    # I dati dell'utente u1 sono spariti da ogni collection user-scoped...
    assert all(d.get("user_id") != "u1" for d in fake_db.clients.docs)
    assert all(d.get("user_id") != "u1" for d in fake_db.offers.docs)
    assert all(d.get("user_id") != "u1" for d in fake_db.documents.docs)
    # ...ma i dati di un ALTRO utente non sono toccati
    assert any(d.get("user_id") == "u2" for d in fake_db.clients.docs)
    # L'utente stesso è stato cancellato
    assert fake_db.users.deleted_one_calls == [{"id": "u1"}]


def test_cancellazione_svuota_anche_notifiche_esecuzioni_automazioni_e_richiesta_demo(
    monkeypatch,
):
    """Regressione: automation_notifications, automation_runs e
    demo_requests contengono dati riconducibili all'utente (user_id, e per
    demo_requests anche nome/email/telefono) ma non erano coperte da
    USER_SCOPED_COLLECTIONS — sarebbero sopravvissute alla cancellazione
    dell'account."""
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(gdpr_mod, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(gdpr_mod, "storage_delete", lambda path: None)

    class FakeSubscriptionService:
        async def cancel_subscription(self, user):
            return {"ok": True}

    monkeypatch.setattr(gdpr_mod, "subscription_service", FakeSubscriptionService())

    service = GdprService()
    run(service.delete_account(USER, "qualunque"))

    assert all(d.get("user_id") != "u1" for d in fake_db.automation_notifications.docs)
    assert all(d.get("user_id") != "u1" for d in fake_db.automation_runs.docs)
    assert all(d.get("user_id") != "u1" for d in fake_db.demo_requests.docs)
    # I dati di un altro utente restano intatti in tutte e tre
    assert any(d.get("user_id") == "u2" for d in fake_db.automation_notifications.docs)
    assert any(d.get("user_id") == "u2" for d in fake_db.automation_runs.docs)
    assert any(d.get("user_id") == "u2" for d in fake_db.demo_requests.docs)


def test_cancellazione_rimuove_il_contatore_ordini_dellutente(monkeypatch):
    """Il contatore progressivo (order_repository.next_order_number) è
    indicizzato per "_id": "order_number:{user_id}", non da un campo
    user_id filtrabile con la query generica usata per le altre collection
    — va ripulito a parte, altrimenti resterebbe orfano nel DB."""
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(gdpr_mod, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(gdpr_mod, "storage_delete", lambda path: None)

    class FakeSubscriptionService:
        async def cancel_subscription(self, user):
            return {"ok": True}

    monkeypatch.setattr(gdpr_mod, "subscription_service", FakeSubscriptionService())

    service = GdprService()
    run(service.delete_account(USER, "qualunque"))

    remaining_ids = [d["_id"] for d in fake_db.counters.docs]
    assert "order_number:u1" not in remaining_ids
    assert "order_number:u2" in remaining_ids


def test_cancellazione_rimuove_i_file_da_s3_non_solo_il_record(monkeypatch):
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(gdpr_mod, "verify_password", lambda plain, hashed: True)

    deleted_paths = []
    monkeypatch.setattr(
        gdpr_mod, "storage_delete", lambda path: deleted_paths.append(path)
    )

    class FakeSubscriptionService:
        async def cancel_subscription(self, user):
            return {"ok": True}

    monkeypatch.setattr(gdpr_mod, "subscription_service", FakeSubscriptionService())

    service = GdprService()
    run(service.delete_account(USER, "qualunque"))

    assert deleted_paths == ["path/to/contratto.pdf"]


def test_cancellazione_traccia_levento_nellaudit_log(monkeypatch):
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(gdpr_mod, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(gdpr_mod, "storage_delete", lambda path: None)

    class FakeSubscriptionService:
        async def cancel_subscription(self, user):
            return {"ok": True}

    monkeypatch.setattr(gdpr_mod, "subscription_service", FakeSubscriptionService())

    service = GdprService()
    run(service.delete_account(USER, "qualunque"))

    assert len(fake_db.admin_audit_log.inserted) == 1
    entry = fake_db.admin_audit_log.inserted[0]
    assert entry["action"] == "self_delete_account"
    assert entry["target_user_id"] == "u1"


def test_audit_log_non_conserva_lemail_in_chiaro(monkeypatch):
    """L'email non deve mai comparire in chiaro nella voce di audit della
    cancellazione (né come 'actor' né altrove): solo il suo hash SHA-256,
    sufficiente a verificare una email indicata da chi in futuro contestasse
    la cancellazione, senza conservare il dato leggibile."""
    import hashlib

    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(gdpr_mod, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(gdpr_mod, "storage_delete", lambda path: None)

    class FakeSubscriptionService:
        async def cancel_subscription(self, user):
            return {"ok": True}

    monkeypatch.setattr(gdpr_mod, "subscription_service", FakeSubscriptionService())

    service = GdprService()
    run(service.delete_account(USER, "qualunque"))

    entry = fake_db.admin_audit_log.inserted[0]
    assert entry["actor"] == "self"
    assert "franco@test.it" not in str(entry)
    assert (
        entry["detail"]["email_hash"] == hashlib.sha256(b"franco@test.it").hexdigest()
    )


def test_export_bloccato_da_troppe_richieste(monkeypatch):
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "check_and_record", _deny_always)

    service = GdprService()
    try:
        run(service.export_user_data(USER))
        assert False, "doveva sollevare HTTPException 429"
    except HTTPException as e:
        assert e.status_code == 429


def test_cancellazione_bloccata_da_troppi_tentativi(monkeypatch):
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "check_and_record", _deny_always)
    monkeypatch.setattr(gdpr_mod, "verify_password", lambda plain, hashed: True)

    service = GdprService()
    try:
        run(service.delete_account(USER, "qualunque"))
        assert False, "doveva sollevare HTTPException 429"
    except HTTPException as e:
        assert e.status_code == 429

    # L'account non deve essere stato toccato: il blocco avviene prima di
    # qualunque effetto collaterale distruttivo.
    assert len(fake_db.users.docs) == 1


def test_tutte_le_collection_dichiarate_esistono_davvero_nel_progetto():
    """Controllo di coerenza: ogni nome di collection dichiarato qui deve
    corrispondere a una collection realmente usata nei repository — previene
    refusi di battitura silenziosi che farebbero credere che una collection
    sia coperta da export/cancellazione quando in realtà non lo è."""
    import subprocess

    result = subprocess.run(
        ["grep", "-rhoP", r"collection = db\.\K[a-z_]+", "repositories/"],
        capture_output=True,
        text=True,
        cwd=".",
    )
    real_collections = set(result.stdout.strip().split("\n"))
    for collection_name in USER_SCOPED_COLLECTIONS.values():
        assert (
            collection_name in real_collections
        ), f"'{collection_name}' non trovata in nessun repository"


def test_ogni_collection_reale_e_classificata():
    """Controllo nella direzione OPPOSTA al test sopra: ogni collection
    MongoDB REALMENTE usata nel codice (repositories/, services/, core/)
    deve comparire o in USER_SCOPED_COLLECTIONS o in
    EXCLUDED_FROM_USER_SCOPED_COLLECTIONS (con una motivazione scritta lì
    accanto per l'esclusione) — mai in nessuno dei due.

    Senza questo controllo, chi introduce una nuova collection con dati
    riconducibili a un utente può dimenticare di collegarla a
    export/cancellazione GDPR senza che nulla lo segnali: è esattamente
    così che automation_notifications, automation_runs e demo_requests sono
    rimaste scoperte finché qualcuno non se n'è accorto a mano. Da qui in
    avanti una collection nuova, non classificata, fa fallire questo test
    finché non viene deliberatamente collocata in uno dei due elenchi.

    Scansione fatta in Python puro (glob + regex), non con un grep esterno
    via subprocess come il test sopra: il pattern qui deve coprire anche
    services/ e core/ (non solo repositories/), e affidarsi al grep di
    sistema qui si è rivelato fragile — un binario diverso trovato nel PATH
    di pytest produceva risultati diversi da quelli della stessa identica
    chiamata da shell."""
    import re
    from pathlib import Path

    pattern = re.compile(r"\bdb\.([a-z_]+)")
    real_collections = set()
    for folder in ("repositories", "services", "core"):
        for path in Path(folder).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            real_collections.update(pattern.findall(path.read_text(encoding="utf-8")))
    assert (
        real_collections
    ), "la scansione non ha trovato nessuna collection: controlla il pattern regex"

    classified = (
        set(USER_SCOPED_COLLECTIONS.values()) | EXCLUDED_FROM_USER_SCOPED_COLLECTIONS
    )
    unclassified = real_collections - classified
    assert not unclassified, (
        f"Collection non classificate in services/gdpr_service.py: {sorted(unclassified)}. "
        "Aggiungile a USER_SCOPED_COLLECTIONS se contengono dati riconducibili a un utente "
        "(export + cancellazione account), o a EXCLUDED_FROM_USER_SCOPED_COLLECTIONS con una "
        "motivazione scritta se non lo sono."
    )
