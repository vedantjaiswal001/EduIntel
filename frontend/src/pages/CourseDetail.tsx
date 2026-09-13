import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar, Cell,
} from "recharts";
import { getCourseHealth, getCourseTopics } from "@/lib/api";
import { PageHeader, Card, SectionTitle, Loading, ErrorState, ChartTooltip, CHART } from "@/components/ui";

export default function CourseDetail() {
  const { id = "" } = useParams();
  const health = useQuery({ queryKey: ["chealth", id], queryFn: () => getCourseHealth(id) });
  const topics = useQuery({ queryKey: ["ctopics", id], queryFn: () => getCourseTopics(id) });

  if (health.isLoading) return <Loading />;
  if (health.isError || !health.data) return <ErrorState message="Course not found." />;
  const h = health.data;
  const comps = Object.entries(h.components).map(([k, v]) => ({ name: k.replace("_", " "), value: v ?? 0 }));

  return (
    <div>
      <PageHeader title={h.course_title} subtitle={h.explanation}
        actions={<Link to="/courses" className="text-sm text-brand-600">← Courses</Link>} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <SectionTitle>Health score</SectionTitle>
          <div className="text-4xl font-semibold text-ink">{h.score ?? "—"}<span className="text-lg text-ink-faint">/100</span></div>
          <div className="mt-1 text-xs text-ink-muted">Pass rate {h.pass_rate != null ? `${Math.round(h.pass_rate * 100)}%` : "—"}</div>
          <div className="mt-4 h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comps} layout="vertical" margin={{ left: 20, right: 10 }}>
                <XAxis type="number" domain={[0, 100]} hide />
                <YAxis type="category" dataKey="name" width={90} fontSize={11} stroke={CHART.axis} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {comps.map((c, i) => <Cell key={i} fill={c.value < 50 ? CHART.high : c.value < 70 ? CHART.medium : CHART.low} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 text-[11px] text-ink-faint">Weights: {Object.entries(h.weights).map(([k, v]) => `${k} ${v}`).join(" · ")}</div>
        </Card>

        <Card className="lg:col-span-2">
          <SectionTitle>Score trend (mean % by assessment)</SectionTitle>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={h.score_trend} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
                <XAxis dataKey="sequence" stroke={CHART.axis} fontSize={12} />
                <YAxis stroke={CHART.axis} fontSize={12} domain={[0, 100]} />
                <Tooltip content={<ChartTooltip />} />
                <Line type="monotone" dataKey="mean_pct" stroke={CHART.brand} strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card className="mt-4">
        <SectionTitle>Topic mastery</SectionTitle>
        {topics.isLoading ? <Loading /> : topics.isError ? <ErrorState /> : (
          <table className="w-full">
            <thead><tr><th className="th">Topic</th><th className="th">Difficulty</th><th className="th">Mastery</th><th className="th">Students</th><th className="th"></th></tr></thead>
            <tbody>
              {topics.data!.map((t) => (
                <tr key={t.topic_id} className="border-t border-surface-100">
                  <td className="td font-medium">{t.name} {t.is_weak && <span className="badge bg-red-50 text-red-600">weak</span>}</td>
                  <td className="td text-ink-muted">{t.difficulty}</td>
                  <td className="td">{t.mastery_pct != null ? `${t.mastery_pct}%` : "—"}</td>
                  <td className="td text-ink-muted">{t.students}</td>
                  <td className="td text-right"><Link to={`/topics/${t.topic_id}`} className="text-xs text-brand-600">drill down →</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
