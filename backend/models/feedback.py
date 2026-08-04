from pydantic import BaseModel, Field
from core.validation_limits import LONG_TEXT_MAX_LENGTH


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str = Field(max_length=LONG_TEXT_MAX_LENGTH)
    # Di default false: un feedback lasciato in app è per uso interno finché
    # l'utente non acconsente esplicitamente a vederlo pubblicato sul sito
    # (vedi feedback_service.list_public, che lo richiede insieme
    # all'approvazione di un admin).
    publish_consent: bool = False
