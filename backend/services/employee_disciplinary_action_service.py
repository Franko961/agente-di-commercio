from core.exceptions import NotFoundError, ValidationAppError
from core.utils import gen_id, now_iso
from repositories.employee_disciplinary_action_repository import (
    employee_disciplinary_action_repository,
)
from repositories.employee_repository import employee_repository


class EmployeeDisciplinaryActionService:
    def __init__(
        self,
        repo=employee_disciplinary_action_repository,
        employees=employee_repository,
    ):
        self.repo = repo
        self.employees = employees

    async def _validate_employee(self, user_id: str, employee_id: str) -> dict:
        employee = await self.employees.find_one(employee_id, user_id)
        if not employee:
            raise ValidationAppError("Dipendente non valido")
        return employee

    async def list_actions(self, user: dict, employee_id: str) -> list:
        await self._validate_employee(user["id"], employee_id)
        return await self.repo.find_many(employee_id, user["id"])

    def _payload_to_doc(self, payload) -> dict:
        return {
            "type": payload.type,
            "subject": payload.subject.strip(),
            "description": (payload.description or "").strip(),
            "event_date": (
                payload.event_date.isoformat() if payload.event_date else None
            ),
            "contestation_date": payload.contestation_date.isoformat(),
            "received_date": (
                payload.received_date.isoformat() if payload.received_date else None
            ),
            "justification_deadline": (
                payload.justification_deadline.isoformat()
                if payload.justification_deadline
                else None
            ),
            "justification_submitted": payload.justification_submitted,
            "justification_date": (
                payload.justification_date.isoformat()
                if payload.justification_date
                else None
            ),
            "outcome": payload.outcome,
            "sanction": (payload.sanction or "").strip(),
            "notes": (payload.notes or "").strip(),
            "document_id": payload.document_id,
        }

    async def create_action(self, user: dict, employee_id: str, payload) -> dict:
        await self._validate_employee(user["id"], employee_id)
        now = now_iso()
        doc = {
            "id": gen_id(),
            "user_id": user["id"],
            "employee_id": employee_id,
            **self._payload_to_doc(payload),
            "created_at": now,
            "updated_at": now,
        }
        return await self.repo.insert(doc)

    async def update_action(
        self, user: dict, employee_id: str, aid: str, payload
    ) -> None:
        ok = await self.repo.update(
            aid,
            user["id"],
            employee_id,
            {
                **self._payload_to_doc(payload),
                "updated_at": now_iso(),
            },
        )
        if not ok:
            raise NotFoundError("Contestazione non trovata")

    async def delete_action(self, user: dict, employee_id: str, aid: str) -> None:
        await self.repo.delete(aid, user["id"], employee_id)


employee_disciplinary_action_service = EmployeeDisciplinaryActionService()
