from pymongo.errors import DuplicateKeyError
from core.database import db
from core.exceptions import ConflictError
from typing import Optional


class AttendanceRepository:
    collection = db.attendance_sessions

    async def find_many(self, employee_id: str, user_id: str) -> list:
        return await self.collection.find(
            {"employee_id": employee_id, "user_id": user_id}, {"_id": 0}
        ).sort("clock_in", -1).to_list(2000)

    async def find_one(self, sid: str, user_id: str) -> Optional[dict]:
        return await self.collection.find_one({"id": sid, "user_id": user_id}, {"_id": 0})

    async def find_open_session(self, employee_id: str, user_id: str) -> Optional[dict]:
        """La sessione ancora aperta (clock_out assente) per questo
        dipendente, se esiste — al massimo una per volta: attendance_service
        rifiuta un secondo ingresso se ce n'è già una aperta, quindi questa
        query non ha mai più di un risultato in condizioni normali."""
        return await self.collection.find_one(
            {"employee_id": employee_id, "user_id": user_id, "clock_out": None}, {"_id": 0}
        )

    async def find_clocked_in_between(self, user_id: str, start_iso: str, end_iso: str) -> list:
        """ID dei dipendenti che hanno almeno una sessione con clock_in
        nell'intervallo [start_iso, end_iso) — una sola query con distinct,
        invece di un find_many() per dipendente (vedi
        attendance_service.today_summary): con poche decine di dipendenti
        la differenza è irrilevante, ma con centinaia diventerebbe una
        classica N+1, oltre a scaricare l'intera cronologia di ciascuno
        (find_many non ha un filtro data) solo per sapere se almeno UNA
        sessione ricade in oggi."""
        return await self.collection.distinct(
            "employee_id", {"user_id": user_id, "clock_in": {"$gte": start_iso, "$lt": end_iso}}
        )

    async def find_all_closed(self, user_id: str) -> list:
        """Tutte le sessioni chiuse (clock_out valorizzato) di TUTTI i
        dipendenti dell'utente — per l'aggregazione ore/giorno della
        griglia di gruppo (Personale → Calendario) e per l'export CSV del
        cartellino (vedi attendance_service.calendar/export_csv). Filtrata
        per mese lato service, non qui: stesso principio già scelto per
        leave_request_repository.find_many (il volume per un account di
        piccola azienda resta gestibile senza un filtro lato query).
        employee_name/note inclusi apposta (a differenza della versione
        precedente, usata solo per il conteggio ore): l'export CSV li
        mostra, il calendario semplicemente li ignora."""
        return await self.collection.find(
            {"user_id": user_id, "clock_out": {"$ne": None}},
            {"_id": 0, "employee_id": 1, "employee_name": 1, "clock_in": 1, "clock_out": 1, "note": 1},
        ).to_list(20000)

    async def insert(self, doc: dict) -> dict:
        # L'indice parziale univoco su (employee_id, user_id) con
        # clock_out=null (vedi startup_service.run_startup) è l'ultima
        # linea di difesa contro due sessioni aperte per lo stesso
        # dipendente: il controllo find_open_session()+insert() in
        # attendance_service non è atomico da solo, quindi due timbrature
        # d'ingresso simultanee potrebbero entrambe superarlo. Qui la
        # seconda insert_one arriva e MongoDB la rifiuta.
        try:
            await self.collection.insert_one(doc)
        except DuplicateKeyError:
            raise ConflictError("Sei già in servizio: registra prima l'uscita")
        doc.pop("_id", None)
        return doc

    async def update(self, sid: str, user_id: str, employee_id: str, data: dict) -> bool:
        # Filtrato anche per employee_id, non solo sid+user_id (stesso
        # principio di employee_document_repository.update_meta): senza,
        # /employees/{eid}/attendance/{sid} accetterebbe una sid che
        # appartiene a un ALTRO dipendente dello stesso utente — non una
        # falla cross-account (user_id resta protetto), ma un'incoerenza
        # semantica tra il percorso e la risorsa davvero modificata.
        res = await self.collection.update_one(
            {"id": sid, "user_id": user_id, "employee_id": employee_id}, {"$set": data}
        )
        return res.matched_count > 0

    async def delete(self, sid: str, user_id: str, employee_id: str) -> None:
        await self.collection.delete_one({"id": sid, "user_id": user_id, "employee_id": employee_id})


attendance_repository = AttendanceRepository()
