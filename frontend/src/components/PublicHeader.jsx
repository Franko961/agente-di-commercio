import { Link, useNavigate } from "react-router-dom";

export default function PublicHeader() {
  const navigate = useNavigate();

  return (
    <header className="border-b border-[#E4E4E1] bg-white px-6 py-4 flex items-center justify-between">
      <Link to="/" className="flex items-center gap-2">
        <div className="w-9 h-9 flex items-center justify-center shrink-0">
          <img src="/logo-mark.png" alt="SALESFLY" className="w-full h-full object-contain" />
        </div>
        <span className="font-cabinet font-black text-lg">SALESFLY.</span>
      </Link>
      <nav className="hidden md:flex items-center gap-6 text-[14px] font-medium text-[#3F3F46]">
        <Link to="/blog" className="hover:text-[#0A192F] transition-colors">Guide</Link>
        <Link to="/prezzi" className="hover:text-[#0A192F] transition-colors">Prezzi</Link>
      </nav>
      <div className="flex items-center gap-3">
        <button onClick={() => navigate("/login")} className="text-[13px] text-[#52525B] hover:text-[#0A192F]">
          Accedi
        </button>
        <button
          onClick={() => navigate("/richiedi-demo")}
          className="px-4 py-2 bg-[#0A192F] text-white rounded-md text-[13px] font-medium hover:bg-[#172A45] transition-colors"
        >
          Inizia gratis
        </button>
      </div>
    </header>
  );
}
