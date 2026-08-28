from core.exceptions import NotFoundError
from core.utils import gen_id, now_iso
from repositories.feedback_repository import feedback_repository


class FeedbackService:
    def __init__(self, repo=feedback_repository):
        self.repo = repo

    async def create(self, user: dict, payload) -> dict:
        doc = {
            "id": gen_id(),
            "user_id": user["id"],
            # Nome copiato al momento dell'invio: se l'utente lo cambia in
            # seguito, un feedback già pubblicato in home page non deve
            # cambiare firma retroattivamente.
            "user_name": user.get("name", ""),
            "rating": payload.rating,
            "text": payload.text.strip(),
            "publish_consent": bool(payload.publish_consent),
            "approved": False,
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def list_all(self) -> list:
        return await self.repo.find_many()

    async def list_public(self) -> list:
        # Solo nome, voto e testo: niente user_id o altri dati interni su un
        # endpoint pubblico non autenticato usato dalla home page.
        items = await self.repo.find_public()
        return [
            {"name": i["user_name"], "rating": i["rating"], "text": i["text"]}
            for i in items
        ]

    async def set_approved(self, fid: str, approved: bool) -> None:
        if not await self.repo.find_one(fid):
            raise NotFoundError("Feedback non trovato")
        await self.repo.set_approved(fid, approved)

    async def delete(self, fid: str) -> None:
        if not await self.repo.find_one(fid):
            raise NotFoundError("Feedback non trovato")
        await self.repo.delete(fid)


feedback_service = FeedbackService()
