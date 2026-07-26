import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { Bell, CheckCheck } from "lucide-react";
import { formatDistanceToNow, parseISO } from "date-fns";
import { it } from "date-fns/locale";
import { Popover, PopoverTrigger, PopoverContent } from "./ui/popover";
import api from "../api";

// Intervallo di aggiornamento del contatore: le automazioni girano ogni 10
// minuti lato server (vedi backend/services/startup_service.py), quindi non
// serve un polling più frequente di così per restare ragionevolmente aggiornati.
const POLL_INTERVAL_MS = 60_000;

export default function NotificationBell() {
  const [notifications, setNotifications] = useState([]);
  const [open, setOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/automations/notifications");
      setNotifications(data);
    } catch {
      // Silenzioso: la campanella non deve mai rompere il resto dell'app
      // se la chiamata fallisce occasionalmente (es. rete instabile).
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [load]);

  const unread = notifications.filter((n) => !n.read);

  const markRead = async (id) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
    try {
      await api.put(`/automations/notifications/${id}/read`);
    } catch {
      load(); // in caso di errore, riallinea allo stato reale del server
    }
  };

  const markAllRead = async () => {
    const ids = unread.map((n) => n.id);
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    await Promise.all(ids.map((id) => api.put(`/automations/notifications/${id}/read`).catch(() => {})));
    load();
  };

  return (
    <Popover open={open} onOpenChange={(v) => { setOpen(v); if (v) load(); }}>
      <PopoverTrigger asChild>
        <button
          data-testid="notification-bell-button"
          className="relative w-9 h-9 flex items-center justify-center rounded-md hover:bg-[#F3F3F1] transition-colors shrink-0"
          aria-label="Notifiche"
        >
          <Bell className="w-[18px] h-[18px] text-[#52525B]" strokeWidth={1.75} />
          {unread.length > 0 && (
            <span
              data-testid="notification-unread-count"
              className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-[#FF5A00] text-white text-[9px] font-mono font-bold flex items-center justify-center"
            >
              {unread.length > 9 ? "9+" : unread.length}
            </span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0 max-h-[70vh] overflow-hidden flex flex-col">
        <div className="px-4 py-3 border-b border-[#E4E4E1] flex items-center justify-between">
          <div className="font-cabinet font-bold text-[13px]">Notifiche</div>
          {unread.length > 0 && (
            <button
              onClick={markAllRead}
              data-testid="mark-all-read-button"
              className="flex items-center gap-1 text-[11px] font-mono uppercase tracking-widest text-[#FF5A00] hover:underline"
            >
              <CheckCheck className="w-3 h-3" /> segna tutte lette
            </button>
          )}
        </div>
        <div className="overflow-y-auto divide-y divide-[#E4E4E1]">
          {notifications.length === 0 && (
            <div className="px-4 py-8 text-center text-[12px] text-[#A1A1AA]">Nessuna notifica</div>
          )}
          {notifications.slice(0, 20).map((n) => (
            <button
              key={n.id}
              data-testid={`notification-${n.id}`}
              onClick={() => !n.read && markRead(n.id)}
              className={`w-full text-left px-4 py-3 hover:bg-[#F9F9F8] transition-colors ${!n.read ? "bg-[#FF5A00]/5" : ""}`}
            >
              <div className="flex items-start gap-2">
                {!n.read && <span className="w-1.5 h-1.5 rounded-full bg-[#FF5A00] shrink-0 mt-1.5" />}
                <div className={`min-w-0 flex-1 ${n.read ? "pl-3.5" : ""}`}>
                  <div className={`text-[12px] ${!n.read ? "font-semibold" : "font-medium text-[#52525B]"} truncate`}>{n.title}</div>
                  <div className="text-[11px] text-[#52525B] mt-0.5 line-clamp-2">{n.message}</div>
                  <div className="font-mono text-[9px] uppercase tracking-widest text-[#A1A1AA] mt-1">
                    {n.created_at && formatDistanceToNow(parseISO(n.created_at), { addSuffix: true, locale: it })}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
        <div className="px-4 py-2.5 border-t border-[#E4E4E1]">
          <Link
            to="/app/automazioni"
            onClick={() => setOpen(false)}
            className="block text-center text-[11px] font-mono uppercase tracking-widest text-[#52525B] hover:text-[#0A0A0A]"
          >
            Vai alle automazioni →
          </Link>
        </div>
      </PopoverContent>
    </Popover>
  );
}
