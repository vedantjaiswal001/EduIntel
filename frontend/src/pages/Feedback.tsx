import { useQuery } from "@tanstack/react-query";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from "recharts";
import { getFeedbackInsights } from "@/lib/api";
import { PageHeader, Card, SectionTitle, Loading, ErrorState, ChartTooltip, CHART } from "@/components/ui";

export default function Feedback() {
  const q = useQuery({ queryKey: ["feedback"], queryFn: () => getFeedbackInsights() });
  if (q.isLoading) return <Loading />;
  if (q.isError || !q.data) return <ErrorState />;
  const d = q.data;
  const issues = d.top_issues.map((i) => ({ name: i.issue, value: i.count }));
  const topicSent = d.topic_sentiment.slice(0, 10).map((t) => ({
    name: t.topic, positive: Math.round(t.positive * 100), neutral: Math.round(t.neutral * 100), negative: Math.round(t.negative * 100),
  }));

  return (
    <div>
      <PageHeader title="Feedback Intelligence" subtitle={`${d.total} responses · sentiment source: ${d.sentiment_source ?? "rating"}`} />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle>Overall sentiment</SectionTitle>
          {(["positive", "neutral", "negative"] as const).map((k) => (
            <div key={k} className="mb-2 flex items-center gap-2 text-sm">
              <span className="w-16 capitalize text-ink-muted">{k}</span>
              <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface-200">
                <div className="h-full rounded-full" style={{ width: `${(d.sentiment[k] ?? 0) * 100}%`, background: k === "positive" ? CHART.low : k === "negative" ? CHART.high : CHART.medium }} />
              </div>
              <span className="w-10 text-right">{Math.round((d.sentiment[k] ?? 0) * 100)}%</span>
            </div>
          ))}
        </Card>
        <Card>
          <SectionTitle>Top student issues</SectionTitle>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={issues} layout="vertical" margin={{ left: 30, right: 20 }}>
                <XAxis type="number" stroke={CHART.axis} fontSize={12} />
                <YAxis type="category" dataKey="name" width={120} fontSize={11} stroke={CHART.axis} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="value" fill={CHART.brand} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card className="mt-4">
        <SectionTitle>Topic-level sentiment (most negative first)</SectionTitle>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={topicSent} margin={{ left: 0, right: 10, bottom: 40 }}>
              <XAxis dataKey="name" angle={-30} textAnchor="end" interval={0} height={70} fontSize={11} stroke={CHART.axis} />
              <YAxis stroke={CHART.axis} fontSize={12} />
              <Tooltip content={<ChartTooltip />} />
              <Legend />
              <Bar dataKey="positive" stackId="s" fill={CHART.low} />
              <Bar dataKey="neutral" stackId="s" fill={CHART.medium} />
              <Bar dataKey="negative" stackId="s" fill={CHART.high} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
