import api from "../api";

// Astrazione per la chat AI pubblica sulla homepage — backend/routers/public_ai.py.
// Nessuna autenticazione, non collegata al CRM: vedi services/public_ai_chat_service.py
// per il perché è tenuta separata dall'assistente reale (api/ai.js).

export function sendPublicAiMessage(payload) {
  return api.post("/public/ai-chat", payload).then(({ data }) => data);
}
