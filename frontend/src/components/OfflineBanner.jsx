import { useEffect, useState } from "react";
import { WifiOff, Wifi } from "lucide-react";

export default function OfflineBanner() {
  const [online, setOnline] = useState(navigator.onLine);
  const [show, setShow] = useState(false);

  useEffect(() => {
    const goOffline = () => { setOnline(false); setShow(true); };
    const goOnline = () => {
      setOnline(true);
      setShow(true);
      setTimeout(() => setShow(false), 2500);
    };
    window.addEventListener("offline", goOffline);
    window.addEventListener("online", goOnline);
    return () => {
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("online", goOnline);
    };
  }, []);

  if (!show && online) return null;

  return (
    <div
      data-testid="offline-banner"
      className={`fixed top-0 inset-x-0 z-[60] flex items-center justify-center gap-2 py-2 px-4 text-[12px] font-mono uppercase tracking-widest transition-all ${
        online ? "bg-[#059669] text-white" : "bg-[#0A0A0A] text-[#FF5A00]"
      }`}
    >
      {online ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
      {online ? "tornato online — sincronizzazione" : "modalità offline — sola lettura"}
    </div>
  );
}
