from core.exceptions import NotFoundError
from core.utils import gen_id, now_iso
from repositories.mandante_repository import mandante_repository


class MandanteService:
    def __init__(self, repo=mandante_repository):
        self.repo = repo

    async def list_mandanti(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_mandante(self, user: dict, payload) -> dict:
        doc = {
            "id": gen_id(),
            "user_id": user["id"],
            **payload.model_dump(),
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def update_mandante(self, user: dict, mid: str, payload) -> None:
        ok = await self.repo.update(mid, user["id"], payload.model_dump())
        if not ok:
            raise NotFoundError("Mandante non trovato")

    async def delete_mandante(self, user: dict, mid: str) -> None:
        await self.repo.delete(mid, user["id"])


mandante_service = MandanteService()
