import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";
import { getWeakTopics } from "@/lib/api";
import { PageHeader, Card, SectionTitle, Loading, ErrorState, ChartTooltip, CHART } from "@/components/ui";

export default function Topics() {
  const q = useQuery({ queryKey: ["weak-topics"], queryFn: () => getWeakTopics(12) });
  if (q.isLoading) return <Loading />;
  if (q.isError || !q.data) return <ErrorState />;
  const chart = q.data.map((t) => ({ name: t.name, value: t.mastery_pct }));

  return (
    <div>
      <PageHeader title="Topic Intelligence" subtitle="Weakest topics platform-wide. Drill into any topic for the student breakdown." />
      <Card>
        <SectionTitle>Weakest topics (mean mastery %)</SectionTitle>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart} layout="vertical" margin={{ left: 40, right: 20 }}>
              <XAxis type="number" domain={[0, 100]} stroke={CHART.axis} fontSize={12} />
              <YAxis type="category" dataKey="name" width={130} fontSize={11} stroke={CHART.axis} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {chart.map((c, i) => <Cell key={i} fill={c.value < 60 ? CHART.high : c.value < 70 ? CHART.medium : CHART.low} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
      <Card className="mt-4">
        <SectionTitle>Details</SectionTitle>
        <table className="w-full">
          <thead><tr><th className="th">Topic</th><th className="th">Course</th><th className="th">Mastery</th><th className="th"></th></tr></thead>
          <tbody>
            {q.data.map((t) => (
              <tr key={t.topic_id} className="border-t border-surface-100">
                <td className="td font-medium">{t.name}</td>
                <td className="td text-ink-muted">{t.course_id}</td>
                <td className="td">{t.mastery_pct}%</td>
                <td className="td text-right"><Link to={`/topics/${t.topic_id}`} className="text-xs text-brand-600">drill down →</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
