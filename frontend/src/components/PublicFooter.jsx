import { Facebook } from "lucide-react";

export default function PublicFooter() {
  return (
    <footer className="border-t border-[#E4E4E1] py-6 px-6">
      <div className="max-w-5xl mx-auto flex items-center justify-center gap-3 text-[12px] text-[#A1A1AA]">
        <span>© 2026 SALESFLY. · Gestionale per agenti di commercio</span>
        <a
          href="https://www.facebook.com/salesflycrm"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="SalesFly su Facebook"
          className="text-[#A1A1AA] hover:text-[#0A192F] transition-colors"
        >
          <Facebook className="w-4 h-4" />
        </a>
      </div>
    </footer>
  );
}
