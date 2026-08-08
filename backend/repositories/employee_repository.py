from core.database import db


class EmployeeRepository:
    collection = db.employees

    async def find_many(self, user_id: str) -> list:
        return await self.collection.find(
            {"user_id": user_id}, {"_id": 0, "request_token_hash": 0, "pin_hash": 0}
        ).sort("name", 1).to_list(1000)

    async def find_one(self, eid: str, user_id: str):
        return await self.collection.find_one(
            {"id": eid, "user_id": user_id}, {"_id": 0, "request_token_hash": 0, "pin_hash": 0}
        )

    async def find_one_with_pin_hash(self, eid: str, user_id: str):
        """Come find_one, ma include pin_hash — uso interno di
        attendance_service._employee_from_kiosk per verificare il PIN al
        chiosco di timbratura. Mai restituito al frontend da questo
        metodo (a differenza di find_one/find_many, che lo escludono
        apposta, stesso principio già applicato a request_token_hash)."""
        return await self.collection.find_one({"id": eid, "user_id": user_id}, {"_id": 0})

    async def find_by_token_hash(self, token_hash: str):
        """Nessun filtro per user_id: l'hash del token (non prevedibile,
        vedi employee_service._generate_token) è quello che identifica sia
        il dipendente sia indirettamente l'azienda — usato dal form
        pubblico di richiesta assenza, che non ha una sessione autenticata
        da cui ricavare lo user_id. request_token_hash NON viene escluso
        qui (a differenza di find_many/find_one): uso interno del
        servizio, mai restituito al frontend da questo metodo."""
        return await self.collection.find_one({"request_token_hash": token_hash}, {"_id": 0})

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update(self, eid: str, user_id: str, data: dict) -> bool:
        res = await self.collection.update_one({"id": eid, "user_id": user_id}, {"$set": data})
        return res.matched_count > 0

    async def touch_last_used(self, eid: str, ts: str) -> None:
        # Senza filtro per user_id (stesso motivo di find_by_token_hash):
        # chiamato dal flusso pubblico non autenticato, dopo che l'hash ha
        # già identificato in modo sicuro il documento giusto.
        await self.collection.update_one({"id": eid}, {"$set": {"last_used_at": ts}})

    async def delete(self, eid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": eid, "user_id": user_id})


employee_repository = EmployeeRepository()
