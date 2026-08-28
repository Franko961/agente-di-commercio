import api from "../api";

// Astrazione per il dominio "spese" — backend/routers/expenses.py.
// Non compreso nell'elenco iniziale di domini, aggiunto per coerenza.

export function listExpenses(params = {}) {
  return api.get("/expenses", { params }).then(({ data }) => data);
}

export function createExpense(payload) {
  return api.post("/expenses", payload).then(({ data }) => data);
}

export function updateExpense(id, payload) {
  return api.put(`/expenses/${id}`, payload).then(({ data }) => data);
}

export function deleteExpense(id) {
  return api.delete(`/expenses/${id}`).then(({ data }) => data);
}
