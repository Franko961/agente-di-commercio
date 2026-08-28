import api from "../api";

// Astrazione per il dominio "prodotti" — backend/routers/products.py.
// Non compreso nell'elenco iniziale di domini, aggiunto per coerenza:
// usato da più pagine (Offers.jsx, Ordini.jsx, Products.jsx).

export function listProducts() {
  return api.get("/products").then(({ data }) => data);
}

export function createProduct(payload) {
  return api.post("/products", payload).then(({ data }) => data);
}

// Non ancora usata da nessuna pagina (nessun import bulk prodotti in UI
// oggi) — esposta qui solo perché il router backend la offre.
export function bulkImportProducts(payload) {
  return api.post("/products/bulk", payload).then(({ data }) => data);
}

export function updateProduct(id, payload) {
  return api.put(`/products/${id}`, payload).then(({ data }) => data);
}

export function deleteProduct(id) {
  return api.delete(`/products/${id}`).then(({ data }) => data);
}
