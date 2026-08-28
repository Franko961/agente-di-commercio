import api from "../api";

// Astrazione per il dominio "ordini" — backend/routers/orders.py.

export function listOrders(params = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.append(k, v);
  }
  const query = qs.toString();
  return api.get(`/orders${query ? `?${query}` : ""}`).then(({ data }) => data);
}

export function listOrdersByClient(clientId) {
  return api.get(`/orders/client/${clientId}`).then(({ data }) => data);
}

export function getOrder(id) {
  return api.get(`/orders/${id}`).then(({ data }) => data);
}

export function createOrder(payload) {
  return api.post("/orders", payload).then(({ data }) => data);
}

export function updateOrder(id, payload) {
  return api.put(`/orders/${id}`, payload).then(({ data }) => data);
}

export function updateOrderStatus(id, payload) {
  return api.patch(`/orders/${id}/status`, payload).then(({ data }) => data);
}

export function deleteOrder(id) {
  return api.delete(`/orders/${id}`).then(({ data }) => data);
}
