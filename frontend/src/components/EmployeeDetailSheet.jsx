import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  User, CalendarDays, Palmtree, Clock, Thermometer, Timer, Truck,
  Package, FileText, AlertTriangle, Wallet, History, Sparkles, Link2, BarChart3,
} from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "./ui/sheet";
import {
  getEmployeeDetail, regenerateEmployeeToken, setEmployeeActive,
  setLeaveRequestCertificate, regenerateEmployeePin,
} from "../api/employees";
import EmployeeSidebar from "./employee-detail/EmployeeSidebar";
import InfoTab from "./employee-detail/tabs/InfoTab";
import AssenzeTab from "./employee-detail/tabs/AssenzeTab";
import FerieTab from "./employee-detail/tabs/FerieTab";
import PermessiTab from "./employee-detail/tabs/PermessiTab";
import MalattieTab from "./employee-detail/tabs/MalattieTab";
import PresenzeTab from "./employee-detail/tabs/PresenzeTab";
import MezzoTab from "./employee-detail/tabs/MezzoTab";
import DotazioneTab from "./employee-detail/tabs/DotazioneTab";
import DocumentiTab from "./employee-detail/tabs/DocumentiTab";
import ContestazioniTab from "./employee-detail/tabs/ContestazioniTab";
import CompensiTab from "./employee-detail/tabs/CompensiTab";
import AttivitaTab from "./employee-detail/tabs/AttivitaTab";
import AiTab from "./employee-detail/tabs/AiTab";
import LinkTab from "./employee-detail/tabs/LinkTab";
import KpiTab from "./employee-detail/tabs/KpiTab";

const TABS = [
  ["info", "Informazioni", User],
  ["assenze", "Assenze", CalendarDays],
  ["ferie", "Ferie", Palmtree],
  ["permessi", "Permessi", Clock],
  ["malattie", "Malattie", Thermometer],
  ["presenze", "Presenze", Timer],
  ["mezzo", "Mezzo", Truck],
  ["dotazione", "Dotazione", Package],
  ["documenti", "Documenti", FileText],
  ["contestazioni", "Contestazioni", AlertTriangle],
  ["compensi", "Compensi", Wallet],
  ["attivita", "Attività", History],
  ["ai", "AI", Sparkles],
  ["link", "Link", Link2],
  ["kpi", "KPI", BarChart3],
];

// 13 tab in un'unica riga scorrevole erano troppi da scoprire su
// smartphone (facile non accorgersi che ce ne sono altri fuori schermo):
// raggruppati in 5 categorie sempre visibili, ognuna con i propri
// sotto-tab — ogni tab resta raggiungibile in al massimo 2 tocchi, stessa
// struttura su mobile e desktop (a differenza di un menu a tendina solo
// mobile, che avrebbe reso i due layout incoerenti).
const TAB_GROUPS = [
  { key: "profilo", label: "Profilo", icon: User, tabs: ["info", "ai", "link"] },
  { key: "assenze", label: "Assenze", icon: CalendarDays, tabs: ["assenze", "ferie", "permessi", "malattie", "presenze"] },
  { key: "risorse", label: "Risorse", icon: Truck, tabs: ["mezzo", "dotazione", "documenti", "contestazioni"] },
  { key: "economia", label: "Economia", icon: Wallet, tabs: ["compensi", "kpi"] },
  { key: "attivita_gruppo", label: "Attività", icon: History, tabs: ["attivita"] },
];

export default function EmployeeDetailSheet({ employee, requests, onClose, onEmployeeUpdated, onRequestsChanged }) {
  const [tab, setTab] = useState("info");
  const [detail, setDetail] = useState(null); // { employee, summary, vehicle, next_revisione }
  const [newLink, setNewLink] = useState(null); // { token } — mostrato una sola volta dopo rigenerazione
  const [newPin, setNewPin] = useState(null); // { pin } — mostrato una sola volta dopo generazione

  const loadDetail = async () => {
    setDetail(await getEmployeeDetail(employee.id));
  };
  useEffect(() => { loadDetail(); }, [employee.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const emp = detail?.employee || employee;
  const summary = detail?.summary;

  const myRequests = requests.filter((r) => r.employee_id === employee.id)
    .sort((a, b) => b.date_from.localeCompare(a.date_from));

  const refreshAll = async () => {
    await loadDetail();
    onEmployeeUpdated();
  };

  const regenerateToken = async () => {
    if (!window.confirm(`Rigenerare il link di "${emp.name}"? Il link precedente smetterà subito di funzionare.`)) return;
    const data = await regenerateEmployeeToken(emp.id);
    setNewLink({ token: data.request_token });
    toast.success("Nuovo link generato");
    refreshAll();
  };

  const toggleActive = async () => {
    await setEmployeeActive(emp.id, !emp.active);
    toast.success(emp.active ? "Dipendente disattivato" : "Dipendente riattivato");
    refreshAll();
  };

  const setCertificate = async (rid, received) => {
    await setLeaveRequestCertificate(rid, received);
    toast.success(received ? "Certificato segnato come ricevuto" : "Certificato segnato come non ricevuto");
    onRequestsChanged();
    loadDetail();
  };

  const copyLink = (token) => {
    const url = `${window.location.origin}/richiedi-assenza/${token}`;
    navigator.clipboard.writeText(url);
    toast.success("Link copiato");
  };

  const regeneratePin = async () => {
    if (emp.has_pin && !window.confirm(`Rigenerare il PIN chiosco di "${emp.name}"? Il PIN precedente smetterà subito di funzionare.`)) return;
    const data = await regenerateEmployeePin(emp.id);
    setNewPin({ pin: data.pin });
    toast.success("Nuovo PIN generato");
    refreshAll();
  };

  return (
    <Sheet open onOpenChange={(v) => !v && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-4xl p-0 flex flex-col">
        <SheetHeader className="px-6 pt-6 pb-0">
          <SheetTitle className="sr-only">Scheda dipendente</SheetTitle>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-6 pb-6 pt-2">
          <div className="flex flex-col md:flex-row gap-6">
            {/* Colonna dashboard, sempre visibile */}
            <EmployeeSidebar employee={emp} summary={summary} vehicle={detail?.vehicle} />

            {/* Contenuto a tab */}
            <div className="flex-1 min-w-0">
              <div className="mb-4">
                {/* Griglia a colonne fisse (non una riga scorrevole): con
                    solo 5 categorie, tutte devono restare visibili senza
                    scroll anche sullo schermo più stretto — è proprio
                    l'assenza di elementi "fuori schermo" a risolvere il
                    problema originale (13 tab in una riga scorrevole). */}
                <div className="grid grid-cols-5 gap-0.5 border-b border-[#E4E4E1]">
                  {TAB_GROUPS.map((group) => {
                    const isActiveGroup = group.tabs.includes(tab);
                    const GroupIcon = group.icon;
                    return (
                      <button key={group.key} onClick={() => { if (!isActiveGroup) setTab(group.tabs[0]); }}
                        className={`flex flex-col items-center justify-end gap-1 px-1 py-2 text-[11px] font-semibold text-center leading-tight border-b-2 -mb-px transition-colors ${
                          isActiveGroup ? "border-[#B23E00] text-[#0A192F]" : "border-transparent text-[#6B6B72] hover:text-[#52525B]"
                        }`}>
                        <GroupIcon className="w-4 h-4 shrink-0" />
                        <span>{group.label}</span>
                      </button>
                    );
                  })}
                </div>
                {(() => {
                  const activeGroup = TAB_GROUPS.find((g) => g.tabs.includes(tab)) || TAB_GROUPS[0];
                  if (activeGroup.tabs.length < 2) return null;
                  return (
                    <div className="flex items-center gap-1 mt-2 overflow-x-auto">
                      {activeGroup.tabs.map((key) => {
                        const [, label, Icon] = TABS.find(([k]) => k === key);
                        return (
                          <button key={key} onClick={() => setTab(key)}
                            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[11px] font-medium whitespace-nowrap transition-colors ${
                              tab === key ? "bg-[#0A192F] text-white" : "bg-[#F3F3F1] text-[#52525B] hover:bg-[#E4E4E1]"
                            }`}>
                            <Icon className="w-3 h-3" /> {label}
                          </button>
                        );
                      })}
                    </div>
                  );
                })()}
              </div>

              {tab === "info" && <InfoTab employee={emp} onSaved={refreshAll} />}
              {tab === "assenze" && <AssenzeTab requests={myRequests} summary={summary} onDeleted={onRequestsChanged} />}
              {tab === "ferie" && <FerieTab summary={summary} />}
              {tab === "permessi" && <PermessiTab summary={summary} />}
              {tab === "malattie" && <MalattieTab summary={summary} onSetCertificate={setCertificate} />}
              {tab === "presenze" && <PresenzeTab employeeId={employee.id} />}
              {tab === "mezzo" && <MezzoTab vehicle={detail?.vehicle} nextRevisione={detail?.next_revisione} />}
              {tab === "dotazione" && <DotazioneTab employeeId={employee.id} />}
              {tab === "documenti" && <DocumentiTab employeeId={employee.id} />}
              {tab === "contestazioni" && <ContestazioniTab employeeId={employee.id} />}
              {tab === "compensi" && <CompensiTab employeeId={employee.id} />}
              {tab === "attivita" && <AttivitaTab employeeId={employee.id} />}
              {tab === "ai" && <AiTab employeeId={employee.id} summary={summary} />}
              {tab === "link" && (
                <LinkTab employee={emp} newLink={newLink} onRegenerate={regenerateToken}
                  onToggleActive={toggleActive} onCopy={copyLink}
                  newPin={newPin} onRegeneratePin={regeneratePin} />
              )}
              {tab === "kpi" && <KpiTab summary={summary} />}
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
