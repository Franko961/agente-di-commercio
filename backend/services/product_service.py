from typing import Optional
from core.utils import gen_id, now_iso
from repositories.product_repository import product_repository


class ProductService:
    def __init__(self, repo=product_repository):
        self.repo = repo

    async def list_products(self, user: dict, mandante_id: Optional[str] = None) -> list:
        return await self.repo.find_many(user["id"], mandante_id)

    async def create_product(self, user: dict, payload) -> dict:
        doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(), "created_at": now_iso()}
        return await self.repo.insert(doc)

    async def update_product(self, user: dict, pid: str, payload) -> None:
        await self.repo.update(pid, user["id"], payload.model_dump())

    async def delete_product(self, user: dict, pid: str) -> None:
        await self.repo.delete(pid, user["id"])


product_service = ProductService()
