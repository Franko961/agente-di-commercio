import { Link } from "react-router-dom";
import { format } from "date-fns";
import { it } from "date-fns/locale";
import { EXTRA_MODULE_META } from "./constants";
import PresenzeWidget from "./PresenzeWidget";

export default function ExtraModulesHome({ user, enabledExtraModules }) {
  return (
    <div className="p-4 md:p-8">
      <div className="border-b border-[#E4E4E1] pb-6 mb-6">
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-2">
          Cruscotto · {format(new Date(), "EEEE d MMMM yyyy", { locale: it })}
        </div>
        <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Buongiorno{user?.name ? `, ${user.name.split(" ")[0]}` : ""}.</h1>
      </div>
      {enabledExtraModules.includes("personale") && (
        <div className="max-w-2xl mb-4">
          <PresenzeWidget />
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl">
        {enabledExtraModules.map((key) => {
          const meta = EXTRA_MODULE_META[key];
          if (!meta) return null;
          const Icon = meta.icon;
          return (
            <Link key={key} to={meta.to} className="bg-white border border-[#E4E4E1] rounded-md p-5 hover:border-[#0A192F] transition-colors">
              <div className="w-10 h-10 bg-[#0A192F] rounded-md flex items-center justify-center mb-3">
                <Icon className="w-5 h-5 text-white" strokeWidth={1.75} />
              </div>
              <div className="font-cabinet font-bold text-[15px] mb-1">{meta.label}</div>
              <p className="text-[13px] text-[#52525B]">{meta.desc}</p>
            </Link>
          );
        })}
      </div>
      {enabledExtraModules.length === 0 && (
        <p className="text-[13px] text-[#6B6B72]">Nessun modulo attivo per questo account al momento.</p>
      )}
    </div>
  );
}
