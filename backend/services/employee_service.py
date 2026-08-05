import secrets

from core.utils import gen_id, now_iso
from core.exceptions import NotFoundError
from core.security import hash_reset_token, module_enabled
from repositories.employee_repository import employee_repository
from repositories.user_repository import user_repository


def _generate_token() -> tuple:
    """Genera il link personale del dipendente in chiaro (da mostrare UNA
    SOLA VOLTA a chi crea/rigenera il dipendente) e il suo hash SHA-256
    (l'unico dato salvato su DB, riusando hash_reset_token già usato per
    il reset password): un dump del database non permette quindi di
    ricostruire i link già emessi. A differenza di un token di reset,
    questo è pensato per essere riusato più volte dallo stesso dipendente
    (link salvato), non consumato una volta sola — per questo, se il
    responsabile lo perde prima di copiarlo, l'unica via è rigenerarlo
    (vedi regenerate_token), invalidando quello precedente."""
    token = secrets.token_urlsafe(24)
    return token, hash_reset_token(token)


class EmployeeService:
    def __init__(self, repo=employee_repository, users=user_repository):
        self.repo = repo
        self.users = users

    async def list_employees(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_employee(self, user: dict, payload) -> dict:
        token, token_hash = _generate_token()
        doc = {
            "id": gen_id(), "user_id": user["id"],
            **payload.model_dump(),
            "request_token_hash": token_hash,
            "last_used_at": None,
            "active": True,
            "created_at": now_iso(),
        }
        await self.repo.insert(doc)
        response = {k: v for k, v in doc.items() if k != "request_token_hash"}
        response["request_token"] = token
        return response

    async def update_employee(self, user: dict, eid: str, payload) -> None:
        ok = await self.repo.update(eid, user["id"], payload.model_dump())
        if not ok:
            raise NotFoundError("Dipendente non trovato")

    async def set_active(self, user: dict, eid: str, active: bool) -> None:
        ok = await self.repo.update(eid, user["id"], {"active": active})
        if not ok:
            raise NotFoundError("Dipendente non trovato")

    async def regenerate_token(self, user: dict, eid: str) -> str:
        """Invalida il link corrente e ne genera uno nuovo: usato quando il
        responsabile ha perso il link originale, o sospetta che sia stato
        condiviso con qualcuno che non doveva riceverlo."""
        token, token_hash = _generate_token()
        ok = await self.repo.update(eid, user["id"], {"request_token_hash": token_hash})
        if not ok:
            raise NotFoundError("Dipendente non trovato")
        return token

    async def delete_employee(self, user: dict, eid: str) -> None:
        await self.repo.delete(eid, user["id"])

    async def get_by_token(self, token: str) -> dict:
        employee = await self.repo.find_by_token_hash(hash_reset_token(token))
        if not employee or not employee.get("active", True):
            raise NotFoundError("Link non valido")
        # Il link resta valido di per sé, ma se il proprietario ha
        # disattivato il modulo Personale dopo averlo generato non deve
        # più essere utilizzabile: la sola verifica su require_module
        # copre le pagine/API autenticate del gestionale, non questo
        # endpoint pubblico, che quindi deve ripeterla qui contro il
        # proprietario (non l'utente autenticato, qui non esiste).
        owner = await self.users.find_by_id(employee["user_id"])
        if not owner or not module_enabled(owner, "personale"):
            raise NotFoundError("Link temporaneamente non disponibile")
        await self.repo.touch_last_used(employee["id"], now_iso())
        return employee


employee_service = EmployeeService()
