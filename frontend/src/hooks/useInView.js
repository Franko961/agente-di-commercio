import { useEffect, useRef, useState } from "react";

// Rileva quando un elemento entra nel viewport, una sola volta (una volta
// vista, una sezione non deve sparire e ricomparire risalendo la pagina —
// l'animazione di ingresso ha senso solo la prima volta).
export default function useInView(options) {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || inView) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setInView(true);
        observer.disconnect();
      }
    }, { threshold: 0.15, ...options });
    observer.observe(el);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return [ref, inView];
}
