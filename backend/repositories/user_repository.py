from typing import Optional

from core.database import db


class UserRepository:
    collection = db.users

    async def find_by_email(self, email: str) -> Optional[dict]:
        return await self.collection.find_one({"email": email})

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def find_by_id(self, uid: str) -> Optional[dict]:
        return await self.collection.find_one(
            {"id": uid}, {"_id": 0, "password_hash": 0}
        )

    async def find_by_reset_token_hash(self, token_hash: str) -> Optional[dict]:
        return await self.collection.find_one({"reset_token_hash": token_hash})

    async def find_by_attendance_kiosk_token_hash(
        self, token_hash: str
    ) -> Optional[dict]:
        """Nessun filtro per id: l'hash del token (non prevedibile, vedi
        attendance_service._generate_kiosk_token) è quello che identifica
        l'azienda — usato dalla pagina pubblica del chiosco di
        timbratura, che non ha una sessione autenticata da cui ricavare
        l'utente. Stesso principio di employee_repository.find_by_token_hash."""
        return await self.collection.find_one(
            {"attendance_kiosk_token_hash": token_hash}, {"_id": 0, "password_hash": 0}
        )

    async def update_by_id(self, uid: str, data: dict) -> None:
        await self.collection.update_one({"id": uid}, {"$set": data})

    async def update_by_stripe_subscription_id(self, sub_id: str, data: dict) -> None:
        await self.collection.update_one(
            {"stripe_subscription_id": sub_id}, {"$set": data}
        )

    async def update_by_paypal_subscription_id(self, sub_id: str, data: dict) -> None:
        await self.collection.update_one(
            {"paypal_subscription_id": sub_id}, {"$set": data}
        )

    async def find_by_paypal_subscription_id(self, sub_id: str) -> Optional[dict]:
        return await self.collection.find_one(
            {"paypal_subscription_id": sub_id}, {"_id": 0, "password_hash": 0}
        )


user_repository = UserRepository()
