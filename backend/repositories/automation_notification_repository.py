from core.database import db


class AutomationNotificationRepository:
    """Notifiche in-app generate dal motore delle automazioni (azione
    'send_reminder'), da mostrare all'utente indipendentemente dal fatto che
    l'email di accompagnamento sia stata consegnata o meno."""

    collection = db.automation_notifications

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def find_many(
        self, user_id: str, unread_only: bool = False, limit: int = 100
    ) -> list:
        query: dict = {"user_id": user_id}
        if unread_only:
            query["read"] = False
        return (
            await self.collection.find(query, {"_id": 0})
            .sort("created_at", -1)
            .to_list(limit)
        )

    async def mark_read(self, nid: str, user_id: str) -> None:
        await self.collection.update_one(
            {"id": nid, "user_id": user_id}, {"$set": {"read": True}}
        )


automation_notification_repository = AutomationNotificationRepository()
