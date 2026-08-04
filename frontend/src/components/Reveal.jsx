import useInView from "@/hooks/useInView";

// Applica l'animazione "fade-up" già definita in index.css quando il blocco
// entra nello scroll, invece che solo al primo caricamento della pagina
// (uso originale della classe in Login.jsx). L'elemento resta invisibile
// (non solo "in attesa") finché non entra in vista, per evitare che compaia
// per un istante prima dell'animazione su connessioni lente.
export default function Reveal({ children, as: Tag = "div", delay = 0, className = "", ...rest }) {
  const [ref, inView] = useInView();
  return (
    <Tag
      ref={ref}
      className={`${inView ? "fade-up" : "opacity-0"} ${className}`}
      style={inView && delay ? { animationDelay: `${delay}ms` } : undefined}
      {...rest}
    >
      {children}
    </Tag>
  );
}
