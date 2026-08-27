import { ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { MiniStat } from "./AssenzeTab";

export default function FerieTab({ summary }) {
  if (!summary) return null;
  const { spettanti, godute, residue } = summary.ferie;
  const data = [
    { name: "Godute", value: godute, color: "#B23E00" },
    { name: "Residue", value: Math.max(residue, 0), color: "#E4E4E1" },
  ];
  return (
    <div>
      <div className="grid grid-cols-3 gap-2 mb-4">
        <MiniStat label="Spettanti" value={spettanti} />
        <MiniStat label="Godute" value={godute} />
        <MiniStat label="Residue" value={residue} />
      </div>
      <div className="bg-white border border-[#E4E4E1] rounded-md p-4 h-56">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
              {data.map((d, i) => <Cell key={i} fill={d.color} />)}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
