import api from "../api";

// Astrazione per il dominio "assistente AI" — backend/routers/ai.py
// (services/ai_service/ lato backend, vedi audit_workflow_pattern per il
// refactor in package di quel modulo).

export function sendAiChatMessage(payload) {
  return api.post("/ai/chat", payload).then(({ data }) => data);
}

export function getAiHistory() {
  return api.get("/ai/history").then(({ data }) => data);
}

export function clearAiHistory() {
  return api.delete("/ai/history").then(({ data }) => data);
}

export function getAiPendingActions() {
  return api.get("/ai/pending-actions").then(({ data }) => data);
}

export function getAiActions(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return api.get(`/ai/actions${qs ? `?${qs}` : ""}`).then(({ data }) => data);
}

export function executeAiAction(payload) {
  return api.post("/ai/execute-action", payload).then(({ data }) => data);
}

export function cancelAiAction(payload) {
  return api.post("/ai/cancel-action", payload).then(({ data }) => data);
}

export function getAiBriefing() {
  return api.get("/ai/briefing").then(({ data }) => data);
}

export function getAiSuggestions() {
  return api.get("/ai/suggestions").then(({ data }) => data);
}

// blob: registrazione audio da MediaRecorder (vedi hooks/useVoiceRecording.js)
// — trascritta lato server (Whisper) al posto del riconoscimento vocale
// nativo del browser, che Safari/WebKit non implementa (assente su ogni
// browser su iPhone).
export function transcribeAudio(blob) {
  // L'estensione dichiarata dovrebbe rispecchiare il formato reale (Safari
  // registra in audio/mp4, non webm) — Whisper riconosce comunque il
  // contenuto vero, ma farla combaciare evita un disallineamento inutile.
  const ext = blob.type.includes("mp4") ? "mp4" : blob.type.includes("ogg") ? "ogg" : "webm";
  const formData = new FormData();
  formData.append("file", blob, `voice.${ext}`);
  return api.post("/ai/transcribe", formData).then(({ data }) => data);
}
