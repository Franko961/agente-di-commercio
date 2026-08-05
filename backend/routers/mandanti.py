from fastapi import APIRouter, Depends
from core.security import get_current_user, forbid_demo_write, require_module
from services.mandante_service import mandante_service
from models.mandante import MandanteIn

router = APIRouter(prefix="/api/mandanti", tags=["mandanti"])

# Solo le scritture legate al modulo "mandanti": la lettura resta sempre
# disponibile perché il selettore "mandante attivo" (MandanteContext, in
# ogni pagina) e i form di Clienti/Prodotti/Offerte/Ordini/Provvigioni la
# usano continuamente — bloccarla romperebbe l'intera app, non solo la
# pagina Mandanti.
MODULE_DEP = Depends(require_module("mandanti"))


@router.get("")
async def list_mandanti(user=Depends(get_current_user)):
    return await mandante_service.list_mandanti(user)


@router.post("", dependencies=[MODULE_DEP])
async def create_mandante(payload: MandanteIn, user=Depends(forbid_demo_write)):
    return await mandante_service.create_mandante(user, payload)


@router.put("/{mid}", dependencies=[MODULE_DEP])
async def update_mandante(mid: str, payload: MandanteIn, user=Depends(forbid_demo_write)):
    await mandante_service.update_mandante(user, mid, payload)
    return {"ok": True}


@router.delete("/{mid}", dependencies=[MODULE_DEP])
async def delete_mandante(mid: str, user=Depends(forbid_demo_write)):
    await mandante_service.delete_mandante(user, mid)
    return {"ok": True}

