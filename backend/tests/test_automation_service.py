"""
Verifica AutomationService: oltre a delete_automation() (già copriva la
pulizia dello storico esecuzioni con user_id passato esplicitamente), anche
list_runs() deve restare tenant-scoped nel repository sottostante, non solo
per merito del controllo di proprietà fatto qui nel service.

delete_automation(): oltre a cancellare l'automazione stessa (già scoped
per user_id), deve ripulire lo storico esecuzioni collegato in
automation_runs passando anche lì lo user_id — altrimenti
automation_run_repository.delete_by_automation cancellerebbe per il solo
automation_id, senza isolamento multi-tenant (bug segnalato: un
automation_id di un altro account, se conosciuto/indovinato, avrebbe
comunque cancellato le SUE esecuzioni anche se la cancellazione
dell'automazione stessa fosse fallita per proprietà non corrispondente).

list_runs(): il service verifica già che l'automazione richiesta
appartenga al chiamante (altrimenti ritorna [] subito), ma passava poi
all'automation_run_repository solo l'automation_id — bug segnalato: il
repository sottostante non era tenant-scoped di per sé, un problema anche
se oggi non direttamente sfruttabile (serve comunque indovinare/conoscere
un automation_id di un'automazione PROPRIA per arrivare a questa riga).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_automation_service.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

from services.automation_service import AutomationService


def run(coro):
    return asyncio.run(coro)


class FakeAutomationRepo:
    def __init__(self):
        self.docs = {}

    async def delete(self, aid, user_id):
        doc = self.docs.get(aid)
        if doc and doc["user_id"] == user_id:
            del self.docs[aid]

    async def find_many(self, user_id):
        return [d for d in self.docs.values() if d["user_id"] == user_id]


class FakeRunRepo:
    def __init__(self):
        self.calls = []
        self.runs = []

    async def delete_by_automation(self, automation_id, user_id):
        self.calls.append((automation_id, user_id))

    async def find_many_by_automation(self, automation_id, user_id):
        self.calls.append((automation_id, user_id))
        return [
            r
            for r in self.runs
            if r["automation_id"] == automation_id and r["user_id"] == user_id
        ]


def build_service():
    repo = FakeAutomationRepo()
    run_repo = FakeRunRepo()
    service = AutomationService(repo=repo, run_repo=run_repo, notification_repo=None)
    return service, repo, run_repo


def test_delete_automation_passa_user_id_alla_pulizia_delle_esecuzioni():
    service, repo, run_repo = build_service()
    repo.docs["auto-1"] = {"id": "auto-1", "user_id": "user-1"}

    run(service.delete_automation({"id": "user-1"}, "auto-1"))

    assert run_repo.calls == [("auto-1", "user-1")]


def test_delete_automation_di_un_altro_utente_non_scrive_lo_user_id_sbagliato():
    """Anche se l'automazione non appartiene all'utente (repo.delete è un
    no-op), la pulizia delle esecuzioni viene comunque invocata con lo
    user_id di CHI CHIAMA, mai con quello del proprietario reale: non deve
    mai essere possibile cancellare le esecuzioni di un altro account."""
    service, repo, run_repo = build_service()
    repo.docs["auto-1"] = {"id": "auto-1", "user_id": "proprietario-vero"}

    run(service.delete_automation({"id": "un-altro-utente"}, "auto-1"))

    assert run_repo.calls == [("auto-1", "un-altro-utente")]
    assert "auto-1" in repo.docs  # l'automazione altrui resta intatta


# ---------- list_runs ----------


def test_list_runs_passa_lo_user_id_al_repository():
    service, repo, run_repo = build_service()
    repo.docs["auto-1"] = {"id": "auto-1", "user_id": "user-1"}
    run_repo.runs.append(
        {"automation_id": "auto-1", "user_id": "user-1", "status": "ok"}
    )

    result = run(service.list_runs({"id": "user-1"}, "auto-1"))

    assert run_repo.calls == [("auto-1", "user-1")]
    assert len(result) == 1


def test_list_runs_di_unautomazione_di_un_altro_utente_ritorna_vuoto_senza_interpellare_il_repo():
    """Il controllo di proprietà avviene PRIMA di toccare il repository
    delle esecuzioni: se l'automazione non è dell'utente, find_many_by_automation
    non va nemmeno chiamato."""
    service, repo, run_repo = build_service()
    repo.docs["auto-1"] = {"id": "auto-1", "user_id": "proprietario-vero"}

    result = run(service.list_runs({"id": "un-altro-utente"}, "auto-1"))

    assert result == []
    assert run_repo.calls == []


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
