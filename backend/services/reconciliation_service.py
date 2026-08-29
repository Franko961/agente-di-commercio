from core.database import db

# (source della spesa generata, campo sulla spesa che punta al documento
# collegato, nome della collection del documento collegato): stesso schema
# per Personale (employee_compensation_service.py) e Flotta
# (vehicle_cost_service.py) — vedi il commento in ReconciliationService.
_LINKED_SOURCES = (
    ("personale", "employee_compensation_id", "employee_compensation"),
    ("flotta", "vehicle_cost_id", "vehicle_costs"),
)

# Scansione non filtrata per utente (guarda TUTTI gli account): un limite
# alto ma finito, stesso ordine di grandezza già usato altrove per scansioni
# globali simili (vedi gdpr_service.delete_account).
_SCAN_LIMIT = 50000


class ReconciliationService:
    """Rileva (senza riparare) le incoerenze tra le spese generate
    automaticamente da un compenso Personale o un costo Flotta
    (services/employee_compensation_service.py, services/vehicle_cost_service.py)
    e il documento che le ha generate.

    Possibili solo perché quel flusso non usa una transazione Mongo (insert
    della spesa, poi insert del compenso/costo, come due operazioni
    separate): se la seconda fallisce dopo che la prima è già andata a buon
    fine — o se update/delete si fermano a metà — un lato resta orfano.
    Il rollback esplicito in creazione (vedi create_compensation/create_cost)
    chiude il caso più probabile; questo scan periodico (vedi
    services/startup/monitoring_jobs.py) è la rete di sicurezza per gli altri.

    Deliberatamente di sola segnalazione: un'incoerenza economica va rivista
    da una persona prima di essere corretta, non riparata in automatico."""

    async def find_inconsistencies(self) -> dict:
        all_expense_ids = {
            e["id"]
            for e in await db.expenses.find({}, {"_id": 0, "id": 1}).to_list(
                _SCAN_LIMIT
            )
        }

        orphan_expenses = (
            []
        )  # spesa Personale/Flotta senza il documento che dovrebbe averla generata
        orphan_links = (
            []
        )  # compenso/costo il cui expense_id non punta a nessuna spesa esistente

        for source, link_field, linked_collection_name in _LINKED_SOURCES:
            linked_collection = db[linked_collection_name]
            linked_ids = {
                d["id"]
                for d in await linked_collection.find({}, {"_id": 0, "id": 1}).to_list(
                    _SCAN_LIMIT
                )
            }

            expenses_for_source = await db.expenses.find(
                {"source": source}, {"_id": 0, "id": 1, "user_id": 1, link_field: 1}
            ).to_list(_SCAN_LIMIT)
            for exp in expenses_for_source:
                if exp.get(link_field) not in linked_ids:
                    orphan_expenses.append(
                        {
                            "expense_id": exp["id"],
                            "user_id": exp["user_id"],
                            "source": source,
                        }
                    )

            linked_docs = await linked_collection.find(
                {}, {"_id": 0, "id": 1, "user_id": 1, "expense_id": 1}
            ).to_list(_SCAN_LIMIT)
            for doc in linked_docs:
                if doc.get("expense_id") not in all_expense_ids:
                    orphan_links.append(
                        {"id": doc["id"], "user_id": doc["user_id"], "source": source}
                    )

        return {"orphan_expenses": orphan_expenses, "orphan_links": orphan_links}


reconciliation_service = ReconciliationService()
