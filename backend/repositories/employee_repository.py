from core.database import db


class EmployeeRepository:
    collection = db.employees

    async def find_many(self, user_id: str) -> list:
        return await self.collection.find({"user_id": user_id}, {"_id": 0}).sort("name", 1).to_list(1000)

    async def find_one(self, eid: str, user_id: str):
        return await self.collection.find_one({"id": eid, "user_id": user_id}, {"_id": 0})

    async def find_by_token(self, token: str):
        """Nessun filtro per user_id: il token stesso, non prevedibile
        (secrets.token_urlsafe, vedi employee_service.create_employee), è
        quello che identifica sia il dipendente sia indirettamente
        l'azienda — usato dal form pubblico di richiesta assenza, che non
        ha una sessione autenticata da cui ricavare lo user_id."""
        return await self.collection.find_one({"request_token": token}, {"_id": 0})

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update(self, eid: str, user_id: str, data: dict) -> bool:
        res = await self.collection.update_one({"id": eid, "user_id": user_id}, {"$set": data})
        return res.matched_count > 0

    async def delete(self, eid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": eid, "user_id": user_id})


employee_repository = EmployeeRepository()
