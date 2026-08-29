from pymongo.errors import DuplicateKeyError

from core.database import db
from core.exceptions import ValidationAppError


class VehicleRepository:
    collection = db.vehicles

    async def find_many(self, user_id: str) -> list:
        return (
            await self.collection.find({"user_id": user_id}, {"_id": 0})
            .sort("plate", 1)
            .to_list(1000)
        )

    async def find_one(self, vid: str, user_id: str):
        return await self.collection.find_one(
            {"id": vid, "user_id": user_id}, {"_id": 0}
        )

    async def find_by_plate(self, plate: str, user_id: str):
        """Usato per il controllo anti-duplicati: `plate` è già normalizzata
        (maiuscolo, senza spazi/trattini) da models.vehicle.normalize_plate
        prima di arrivare qui, quindi il confronto è un match esatto."""
        return await self.collection.find_one(
            {"plate": plate, "user_id": user_id}, {"_id": 0}
        )

    async def insert(self, doc: dict) -> dict:
        # L'indice univoco su (user_id, plate) — vedi services.startup.indexes
        # — è l'ultima linea di difesa contro due mezzi con la stessa targa:
        # find_by_plate() in vehicle_service è già un check preventivo, ma da
        # solo è un check-then-act che due richieste concorrenti potrebbero
        # entrambe superare prima che il primo insert completi.
        try:
            await self.collection.insert_one(doc)
        except DuplicateKeyError:
            raise ValidationAppError(
                f"Esiste già un mezzo con targa {doc.get('plate')}"
            )
        doc.pop("_id", None)
        return doc

    async def update(self, vid: str, user_id: str, data: dict) -> bool:
        try:
            res = await self.collection.update_one(
                {"id": vid, "user_id": user_id}, {"$set": data}
            )
        except DuplicateKeyError:
            raise ValidationAppError(
                f"Esiste già un mezzo con targa {data.get('plate')}"
            )
        return res.matched_count > 0

    async def delete(self, vid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": vid, "user_id": user_id})


vehicle_repository = VehicleRepository()
