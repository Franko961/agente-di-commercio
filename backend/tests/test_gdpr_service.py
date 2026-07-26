"""
Test per gdpr_service: esportazione completa dei dati (art. 20 GDPR) e
cancellazione definitiva dell'account (art. 17 GDPR) — non un soft-delete:
verifica che ogni collection user-scoped venga davvero svuotata e che i file
dei documenti vengano rimossi anche da S3, non solo il loro record.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_gdpr_service.py -v
"""
import sys
import asyncio
import io
import json
import zipfile

sys.path.insert(0, ".")

import services.gdpr_service as gdpr_mod
from services.gdpr_service import GdprService, USER_SCOPED_COLLECTIONS
from fastapi import HTTPException


def run(coro):
    return asyncio.run(coro)


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
        docs = [d for d in self.docs if (user_id is None or d.get("user_id") == user_id)]
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
        self.docs = [d for d in self.docs if d.get("id") != query.get("id")]

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
    fake_db.users.docs.append({
        "id": "u1", "email": "franco@test.it", "name": "Franco",
        "password_hash": "hash-segreto", "plan": "pro",
    })
    fake_db.clients.docs.append({"id": "c1", "user_id": "u1", "company_name": "Bar Centrale"})
    fake_db.clients.docs.append({"id": "c2", "user_id": "u2", "company_name": "Cliente di un altro utente"})
    fake_db.offers.docs.append({"id": "o1", "user_id": "u1", "total": 500})
    fake_db.documents.docs.append({
        "id": "d1", "user_id": "u1", "original_filename": "contratto.pdf",
        "storage_path": "path/to/contratto.pdf",
    })
    return fake_db


def test_export_include_profilo_e_dati_utente(monkeypatch):
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "storage_get", lambda path: (b"contenuto pdf finto", "application/pdf"))
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
    monkeypatch.setattr(gdpr_mod, "storage_get", lambda path: (b"x", "application/pdf"))
    service = GdprService()

    zip_bytes = run(service.export_user_data(USER))
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        data = json.loads(zf.read("dati.json"))

    company_names = [c["company_name"] for c in data["clienti"]]
    assert "Cliente di un altro utente" not in company_names


def test_export_prosegue_se_un_documento_non_si_trova(monkeypatch):
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)

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
    fake_db.users.docs.append({"id": "u1", "email": "franco@test.it", "name": "Franco", "password_hash": "x"})
    fake_db.documents.docs.append({
        "id": "d1", "user_id": "u1", "name": "../../evil.sh",
        "storage_path": "path/to/evil.sh",
        # Nessun original_filename: il caso realistico è un vecchio
        # documento, o uno il cui original_filename manca per qualche
        # motivo, che ricade sul campo 'name' modificabile dall'utente.
    })
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "storage_get", lambda path: (b"contenuto", "application/octet-stream"))
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
    monkeypatch.setattr(gdpr_mod, "verify_password", lambda plain, hashed: plain == "password-giusta")
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


def test_cancellazione_rimuove_i_file_da_s3_non_solo_il_record(monkeypatch):
    fake_db = build_fake_db_with_data()
    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "verify_password", lambda plain, hashed: True)

    deleted_paths = []
    monkeypatch.setattr(gdpr_mod, "storage_delete", lambda path: deleted_paths.append(path))

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


def test_tutte_le_collection_dichiarate_esistono_davvero_nel_progetto():
    """Controllo di coerenza: ogni nome di collection dichiarato qui deve
    corrispondere a una collection realmente usata nei repository — previene
    refusi di battitura silenziosi che farebbero credere che una collection
    sia coperta da export/cancellazione quando in realtà non lo è."""
    import subprocess
    result = subprocess.run(
        ["grep", "-rhoP", r"collection = db\.\K[a-z_]+", "repositories/"],
        capture_output=True, text=True, cwd=".",
    )
    real_collections = set(result.stdout.strip().split("\n"))
    for collection_name in USER_SCOPED_COLLECTIONS.values():
        assert collection_name in real_collections, f"'{collection_name}' non trovata in nessun repository"
