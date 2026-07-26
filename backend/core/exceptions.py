class AppError(Exception):
    status_code = 500
    detail = "Errore interno"

    def __init__(self, detail: str = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    detail = "Risorsa non trovata"


class PermissionDeniedError(AppError):
    status_code = 403
    detail = "Permesso negato"


class ValidationAppError(AppError):
    status_code = 400
    detail = "Dati non validi"


class ConflictError(AppError):
    status_code = 409
    detail = "La risorsa è in conflitto con lo stato attuale"
