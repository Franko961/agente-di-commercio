from typing import Optional
from fastapi import HTTPException
from core.utils import gen_id, now_iso
from repositories.product_repository import product_repository
from repositories.mandante_repository import mandante_repository


class ProductService:
    def __init__(self, repo=product_repository, mandante_repo=mandante_repository):
        self.repo = repo
        self.mandante_repo = mandante_repo

    async def list_products(self, user: dict, mandante_id: Optional[str] = None) -> list:
        return await self.repo.find_many(user["id"], mandante_id)

    async def create_product(self, user: dict, payload) -> dict:
        doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(), "created_at": now_iso()}
        return await self.repo.insert(doc)

    async def update_product(self, user: dict, pid: str, payload) -> None:
        await self.repo.update(pid, user["id"], payload.model_dump())

    async def delete_product(self, user: dict, pid: str) -> None:
        await self.repo.delete(pid, user["id"])

    async def bulk_import(self, user: dict, payload) -> dict:
        """Importa in blocco un listino prodotti (es. da un PDF/Excel
        fornitore) per un mandante già esistente, risolto per nome come già
        avviene altrove nell'app (es. client_name nelle offerte AI).

        Idempotente rispetto allo SKU: se un prodotto con lo stesso sku
        esiste già per questo mandante, viene SALTATO (non aggiornato, non
        duplicato) — così l'endpoint può essere richiamato più volte in modo
        sicuro (es. per completare un'importazione interrotta) senza mai
        creare doppioni."""
        mand = await self.mandante_repo.find_by_name_regex(user["id"], payload.mandante_name)
        if not mand:
            raise HTTPException(404, f"Mandante '{payload.mandante_name}' non trovato nel CRM.")

        existing = await self.repo.find_many(user["id"], mand["id"])
        existing_skus = {p.get("sku") for p in existing if p.get("sku")}

        to_insert = []
        skipped = []
        for item in payload.products:
            if item.sku in existing_skus:
                skipped.append(item.sku)
                continue
            to_insert.append({
                "id": gen_id(), "user_id": user["id"], "mandante_id": mand["id"],
                "name": item.name, "sku": item.sku, "price": item.price,
                "cost": item.cost or 0.0, "commission_rate": item.commission_rate,
                "category": item.category or "", "created_at": now_iso(),
            })

        await self.repo.insert_many(to_insert)
        return {
            "mandante_id": mand["id"],
            "mandante_name": mand["name"],
            "imported": len(to_insert),
            "skipped_existing": len(skipped),
            "skipped_skus": skipped,
            "total_requested": len(payload.products),
        }


product_service = ProductService()
