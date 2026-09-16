from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from core.validation_limits import LONG_TEXT_MAX_LENGTH

# Storico breve mandato dal frontend ad ogni richiesta (nessuno storico
# persistito lato server — vedi public_ai_chat_service.py): basta il minimo
# per dare all'AI un po' di contesto sulla conversazione in corso.
PUBLIC_CHAT_HISTORY_MAX_MESSAGES = 6


class PublicChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=LONG_TEXT_MAX_LENGTH)


class PublicAiChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=LONG_TEXT_MAX_LENGTH)
    history: Optional[List[PublicChatHistoryItem]] = Field(
        default=None, max_length=PUBLIC_CHAT_HISTORY_MAX_MESSAGES
    )
