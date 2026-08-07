from repositories.user_repository import user_repository

# Unico default rimasto: l'obiettivo di fatturato, per compatibilità con gli
# utenti esistenti che non hanno ancora impostato il proprio (prima era una
# costante globale uguale per tutti — questo valore la sostituisce solo come
# fallback quando l'utente non ne ha scelto uno). Le altre tre metriche non
# esistevano prima, quindi non hanno un default: restano "non impostate"
# finché l'utente non le configura.
DEFAULT_GOAL_REVENUE = 10000


class SettingsService:
    def __init__(self, repo=user_repository):
        self.repo = repo

    @staticmethod
    def _goals_view(user: dict) -> dict:
        return {
            "goal_revenue": user.get("goal_revenue") if user.get("goal_revenue") is not None else DEFAULT_GOAL_REVENUE,
            "goal_commissions": user.get("goal_commissions"),
            "goal_new_clients": user.get("goal_new_clients"),
            "goal_visits": user.get("goal_visits"),
        }

    async def get_goals(self, user: dict) -> dict:
        return self._goals_view(user)

    async def update_goals(self, user: dict, payload) -> dict:
        # exclude_unset: un campo omesso dalla richiesta resta invariato,
        # invece di essere azzerato — permette di aggiornare un solo
        # obiettivo alla volta senza dover rimandare tutti gli altri.
        data = payload.model_dump(exclude_unset=True)
        await self.repo.update_by_id(user["id"], data)
        return self._goals_view({**user, **data})

    @staticmethod
    def _addresses_view(user: dict) -> dict:
        return {
            "home_address": user.get("home_address"),
            "home_lat": user.get("home_lat"),
            "home_lng": user.get("home_lng"),
            "office_address": user.get("office_address"),
            "office_lat": user.get("office_lat"),
            "office_lng": user.get("office_lng"),
        }

    async def get_addresses(self, user: dict) -> dict:
        return self._addresses_view(user)

    async def update_addresses(self, user: dict, payload) -> dict:
        data = payload.model_dump(exclude_unset=True)
        await self.repo.update_by_id(user["id"], data)
        return self._addresses_view({**user, **data})

    @staticmethod
    def _leave_view(user: dict) -> dict:
        return {"ferie_count_mode": user.get("ferie_count_mode", "calendario")}

    async def get_leave_settings(self, user: dict) -> dict:
        return self._leave_view(user)

    async def update_leave_settings(self, user: dict, payload) -> dict:
        data = payload.model_dump()
        await self.repo.update_by_id(user["id"], data)
        return self._leave_view({**user, **data})


settings_service = SettingsService()
