import { useEffect, useState } from "react";
import api from "../api";

// Colori puramente visivi per piano — non sono dati di business, restano qui
// invece che nel backend. Se aggiungi un piano nuovo, aggiungi anche il colore.
const PLAN_COLORS = {
  base: "#0A192F",
  pro: "#B23E00",
};

// Cache a livello di modulo: più pagine usano questo hook nella stessa sessione
// (Landing, Pricing, Login, Subscription) e non ha senso rifare la stessa
// chiamata di rete per ognuna — i piani cambiano raramente.
let cache = null;
let inflight = null;

async function fetchPlans() {
  if (cache) return cache;
  if (!inflight) {
    inflight = api.get("/subscription/plans").then(({ data }) => {
      cache = data;
      return data;
    });
  }
  return inflight;
}

/**
 * Fonte unica di verità per piani, prezzi e durata del trial nel frontend.
 * Tutto arriva da GET /api/subscription/plans, che a sua volta legge da
 * core/config.py sul backend — niente prezzi o nomi piano scritti a mano
 * nelle pagine.
 */
export default function usePlans() {
  const [data, setData] = useState(cache);
  const [loading, setLoading] = useState(!cache);

  useEffect(() => {
    if (cache) return;
    let active = true;
    fetchPlans().then((d) => {
      if (active) {
        setData(d);
        setLoading(false);
      }
    });
    return () => { active = false; };
  }, []);

  const plansById = {};
  for (const p of data?.plans || []) {
    plansById[p.id] = { ...p, color: PLAN_COLORS[p.id] || "#0A192F" };
  }

  return {
    loading,
    plans: data?.plans || [],
    plansById,
    trialDays: data?.trial_days ?? 14, // fallback solo per il primo render prima che arrivi la risposta
  };
}
