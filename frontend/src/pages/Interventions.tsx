import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";
import { getEffectiveness, listInterventions } from "@/lib/api";
import { PageHeader, Card, SectionTitle, StatCard, Loading, ErrorState, ChartTooltip, CHART } from "@/components/ui";

export default function Interventions() {
  const eff = useQuery({ queryKey: ["effectiveness"], queryFn: getEffectiveness });
  const list = useQuery({ queryKey: ["interventions"], queryFn: () => listInterventions() });

  if (eff.isLoading) return <Loading />;
  if (eff.isError || !eff.data) return <ErrorState />;
  const e = eff.data;
  const byType = e.by_type ? Object.entries(e.by_type).map(([k, v]) => ({ name: k, value: v.mean_delta })) : [];

  return (
    <div>
      <PageHeader title="Intervention Center" subtitle="Recommended actions, records, and measured before/after outcomes." />
      {e.n === 0 ? (
        <Card><div className="text-sm text-ink-muted">No interventions recorded. Run scripts/seed_interventions.py.</div></Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Interventions" value={e.n} />
            <StatCard label="Mean change" value={e.mean_delta != null ? `${e.mean_delta > 0 ? "+" : ""}${e.mean_delta}` : "—"} sub="points" />
            <StatCard label="Improved" value={e.improved_share != null ? `${Math.round(e.improved_share * 100)}%` : "—"} />
            <StatCard label="Types" value={byType.length} />
          </div>

          <Card className="mt-4">
            <SectionTitle>Mean change by intervention type</SectionTitle>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={byType} margin={{ left: 0, right: 10 }}>
                  <XAxis dataKey="name" fontSize={11} stroke={CHART.axis} />
                  <YAxis fontSize={12} stroke={CHART.axis} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {byType.map((b, i) => <Cell key={i} fill={b.value >= 0 ? CHART.low : CHART.high} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            {e.caveat && <p className="mt-2 rounded bg-amber-50 px-3 py-2 text-xs text-amber-800">{e.caveat}</p>}
          </Card>

          <Card className="mt-4">
            <SectionTitle>Recorded interventions</SectionTitle>
            {list.isLoading ? <Loading /> : (
              <div className="max-h-96 overflow-y-auto">
                <table className="w-full">
                  <thead><tr><th className="th">Student</th><th className="th">Type</th><th className="th">Before</th><th className="th">After</th><th className="th text-right">Δ</th></tr></thead>
                  <tbody>
                    {list.data!.map((iv) => {
                      const o = iv.outcomes[0];
                      return (
                        <tr key={iv.id} className="border-t border-surface-100">
                          <td className="td"><Link to={`/students/${iv.student_id}`} className="text-brand-600 hover:underline">{iv.student_id}</Link></td>
                          <td className="td capitalize">{iv.type}</td>
                          <td className="td">{o?.before ?? "—"}</td>
                          <td className="td">{o?.after ?? "—"}</td>
                          <td className={`td text-right font-medium ${o && o.delta >= 0 ? "text-emerald-600" : "text-red-600"}`}>{o ? (o.delta >= 0 ? `+${o.delta}` : o.delta) : "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
