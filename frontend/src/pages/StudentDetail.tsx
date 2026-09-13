import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar, Cell,
} from "recharts";
import { getStudent, getRisk, getTrajectory, getRecommendations, listInterventions } from "@/lib/api";
import { PageHeader, Card, SectionTitle, Loading, ErrorState, RiskBadge, ProgressBar, ChartTooltip, CHART } from "@/components/ui";

export default function StudentDetail() {
  const { id = "" } = useParams();
  const student = useQuery({ queryKey: ["student", id], queryFn: () => getStudent(id) });
  const risk = useQuery({ queryKey: ["risk", id], queryFn: () => getRisk(id), retry: false });
  const traj = useQuery({ queryKey: ["traj", id], queryFn: () => getTrajectory(id), retry: false });
  const recs = useQuery({ queryKey: ["recs", id], queryFn: () => getRecommendations(id), retry: false });
  const ivs = useQuery({ queryKey: ["ivs", id], queryFn: () => listInterventions(id), retry: false });

  if (student.isLoading) return <Loading />;
  if (student.isError || !student.data) return <ErrorState message="Student not found." />;

  const shap = risk.data?.shap_values?.top_factors
    ?.filter((f) => f.shap > 0).slice(0, 6)
    .map((f) => ({ name: f.label, value: Number(f.shap.toFixed(3)) })) ?? [];

  // merge score + risk trajectory by week for a combined chart
  const scoreByWeek = new Map<number, any>();
  traj.data?.score_series.forEach((s) => scoreByWeek.set(s.week, { week: s.week, score: s.mean_pct }));
  traj.data?.risk_trajectory.forEach((r) => {
    const e = scoreByWeek.get(r.week) || { week: r.week };
    e.risk = Math.round(r.risk_probability * 100);
    scoreByWeek.set(r.week, e);
  });
  const trajData = Array.from(scoreByWeek.values()).sort((a, b) => a.week - b.week);

  return (
    <div>
      <PageHeader
        title={`${student.data.name}`}
        subtitle={`${student.data.id} · ${student.data.program} · prior GPA ${student.data.prev_gpa ?? "—"}`}
        actions={<Link to="/students" className="text-sm text-brand-600">← All students</Link>}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* risk + shap */}
        <Card>
          <SectionTitle>Overall risk</SectionTitle>
          {risk.isError ? <div className="text-sm text-ink-muted">No prediction (train the model).</div> : risk.isLoading ? <Loading /> : (
            <>
              <div className="flex items-center gap-3">
                <RiskBadge level={risk.data!.risk_label} />
                <span className="text-2xl font-semibold text-ink">{Math.round(risk.data!.risk_probability * 100)}%</span>
                <span className="text-xs text-ink-muted">P(high)</span>
              </div>
              {shap.length > 0 && (
                <div className="mt-4">
                  <div className="stat-label mb-1">Top contributing factors (SHAP)</div>
                  <div className="h-40">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={shap} layout="vertical" margin={{ left: 10, right: 10 }}>
                        <XAxis type="number" hide />
                        <YAxis type="category" dataKey="name" width={110} fontSize={11} stroke={CHART.axis} />
                        <Tooltip content={<ChartTooltip />} />
                        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                          {shap.map((_, i) => <Cell key={i} fill={CHART.high} />)}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
              {risk.data?.explanation && <p className="mt-3 text-xs leading-relaxed text-ink-muted">{risk.data.explanation}</p>}
            </>
          )}
        </Card>

        {/* trajectory */}
        <Card className="lg:col-span-2">
          <SectionTitle right={traj.data?.summary && <span className={`text-xs ${traj.data.summary.deteriorating ? "text-red-600" : "text-ink-muted"}`}>{traj.data.summary.trend}</span>}>
            Performance & risk trajectory
          </SectionTitle>
          {traj.isError ? <ErrorState /> : traj.isLoading ? <Loading /> : (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trajData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
                  <XAxis dataKey="week" stroke={CHART.axis} fontSize={12} label={{ value: "week", position: "insideBottom", offset: -2, fontSize: 11 }} />
                  <YAxis stroke={CHART.axis} fontSize={12} domain={[0, 100]} />
                  <Tooltip content={<ChartTooltip />} />
                  <Line type="monotone" dataKey="score" name="score %" stroke={CHART.brand} strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="risk" name="risk %" stroke={CHART.high} strokeWidth={2} strokeDasharray="4 3" dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* topic mastery */}
        <Card>
          <SectionTitle>Topic mastery (weakest first)</SectionTitle>
          {traj.data?.topic_mastery?.length ? (
            <div className="space-y-2">
              {traj.data.topic_mastery.slice(0, 8).map((t) => (
                <div key={t.topic_id} className="flex items-center gap-2 text-sm">
                  <span className="w-24 truncate text-ink-muted" title={t.topic_id}>{t.topic_id}</span>
                  <div className="flex-1"><ProgressBar value={t.mastery_pct} tone="risk" /></div>
                  <span className="w-10 text-right text-ink-soft">{t.mastery_pct}%</span>
                </div>
              ))}
            </div>
          ) : <div className="text-sm text-ink-muted">No mastery data.</div>}
        </Card>

        {/* recommendations */}
        <Card>
          <SectionTitle>Recommended interventions</SectionTitle>
          {recs.data?.recommendations?.length ? (
            <ol className="space-y-2">
              {recs.data.recommendations.map((r, i) => (
                <li key={i} className="text-sm">
                  <span className="font-medium capitalize text-ink">{r.type}</span>
                  {r.target_topic && <span className="text-ink-muted"> · {r.target_topic}</span>}
                  <div className="text-xs text-ink-muted">{r.reason}</div>
                </li>
              ))}
            </ol>
          ) : <div className="text-sm text-ink-muted">No recommendations.</div>}
          {recs.data?.note && <p className="mt-3 text-xs italic text-ink-faint">{recs.data.note}</p>}
        </Card>
      </div>

      <Card className="mt-4">
        <SectionTitle>Intervention history</SectionTitle>
        {ivs.data?.length ? (
          <table className="w-full">
            <thead><tr><th className="th">Type</th><th className="th">Status</th><th className="th">Before</th><th className="th">After</th><th className="th text-right">Δ</th></tr></thead>
            <tbody>
              {ivs.data.map((iv) => {
                const o = iv.outcomes[0];
                return (
                  <tr key={iv.id} className="border-t border-surface-100">
                    <td className="td capitalize">{iv.type}</td>
                    <td className="td text-ink-muted">{iv.status}</td>
                    <td className="td">{o ? o.before : "—"}</td>
                    <td className="td">{o ? o.after : "—"}</td>
                    <td className={`td text-right font-medium ${o && o.delta >= 0 ? "text-emerald-600" : "text-red-600"}`}>{o ? (o.delta >= 0 ? `+${o.delta}` : o.delta) : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : <div className="text-sm text-ink-muted">No interventions recorded.</div>}
      </Card>
    </div>
  );
}
