import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell,
} from "recharts";
import { Users, AlertTriangle, TrendingUp, CalendarCheck, Sparkles, Bell } from "lucide-react";
import { getDashboard, getAtRisk } from "@/lib/api";
import { PageHeader, StatCard, Card, SectionTitle, Loading, ErrorState, SeverityDot, ChartTooltip, CHART } from "@/components/ui";

const RISK_COLORS: Record<string, string> = { LOW_RISK: CHART.low, MEDIUM_RISK: CHART.medium, HIGH_RISK: CHART.high };

export default function Dashboard() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["dashboard"], queryFn: getDashboard });
  const atRisk = useQuery({ queryKey: ["atrisk", 6], queryFn: () => getAtRisk(6) });

  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorState />;

  const risk = data.risk_distribution ? Object.entries(data.risk_distribution).map(([name, value]) => ({ name, value })) : [];
  const totalRisk = risk.reduce((s, r) => s + r.value, 0);
  const sent = data.feedback_sentiment;

  return (
    <div>
      <PageHeader title="Executive Dashboard" subtitle="Institution-wide risk, performance, engagement and feedback intelligence." />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Students" value={data.totals.students} icon={Users} accent="brand" sub={`${data.totals.courses} courses`} />
        <StatCard label="At risk (HIGH)" value={data.risk_distribution?.HIGH_RISK ?? "—"} icon={AlertTriangle} accent="red" sub="needs intervention" />
        <StatCard label="Avg performance" value={data.avg_performance != null ? `${data.avg_performance}%` : "—"} icon={TrendingUp} accent="violet" />
        <StatCard label="Attendance" value={data.attendance_avg != null ? `${data.attendance_avg}%` : "—"} icon={CalendarCheck} accent="emerald" />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionTitle>Performance trend <span className="font-normal text-ink-faint">· mean % by assessment</span></SectionTitle>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.performance_trend} margin={{ top: 5, right: 10, left: -12, bottom: 0 }}>
                <defs>
                  <linearGradient id="perfFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={CHART.brand} stopOpacity={0.28} />
                    <stop offset="100%" stopColor={CHART.brand} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="4 4" stroke={CHART.grid} vertical={false} />
                <XAxis dataKey="sequence" stroke={CHART.axis} fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke={CHART.axis} fontSize={12} domain={[0, 100]} tickLine={false} axisLine={false} />
                <Tooltip content={<ChartTooltip unit="%" />} />
                <Area type="monotone" dataKey="mean_pct" name="mean" stroke={CHART.brand} strokeWidth={2.5} fill="url(#perfFill)" dot={{ r: 3, fill: CHART.brand }} activeDot={{ r: 5 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <SectionTitle>Risk distribution</SectionTitle>
          {risk.length ? (
            <div className="relative h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={risk} dataKey="value" nameKey="name" innerRadius={54} outerRadius={80} paddingAngle={3} strokeWidth={0}>
                    {risk.map((r) => <Cell key={r.name} fill={RISK_COLORS[r.name] || CHART.brand} />)}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <div className="font-display text-2xl font-bold text-ink">{totalRisk}</div>
                <div className="text-[11px] text-ink-muted">students</div>
              </div>
            </div>
          ) : <div className="py-10 text-center text-sm text-ink-muted">Train the model to populate risk.</div>}
          <div className="mt-3 flex justify-center gap-3 text-xs">
            {risk.map((r) => (
              <span key={r.name} className="flex items-center gap-1.5 text-ink-soft">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: RISK_COLORS[r.name] }} />
                {r.name.replace("_RISK", "")} {r.value}
              </span>
            ))}
          </div>
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <SectionTitle>Feedback sentiment</SectionTitle>
          {sent?.n ? (
            <div className="space-y-3">
              {(["positive", "neutral", "negative"] as const).map((k) => (
                <div key={k} className="flex items-center gap-3 text-sm">
                  <span className="w-16 capitalize text-ink-muted">{k}</span>
                  <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface-200">
                    <div className="h-full rounded-full transition-all duration-500" style={{ width: `${(sent as any)[k] * 100}%`, background: k === "positive" ? CHART.low : k === "negative" ? CHART.high : CHART.medium }} />
                  </div>
                  <span className="w-10 text-right font-semibold text-ink-soft">{Math.round((sent as any)[k] * 100)}%</span>
                </div>
              ))}
              <div className="pt-1 text-xs text-ink-muted">{sent.n} responses</div>
            </div>
          ) : <div className="text-sm text-ink-muted">No feedback.</div>}
        </Card>

        <Card>
          <SectionTitle right={<Bell className="h-4 w-4 text-ink-faint" />}>Recent alerts</SectionTitle>
          <div className="space-y-2.5">
            {data.recent_alerts.length ? data.recent_alerts.map((a, i) => (
              <div key={i} className="flex items-start gap-2.5 text-sm">
                <span className="mt-1"><SeverityDot severity={a.severity} /></span>
                <span className="text-ink-soft">{a.message}</span>
              </div>
            )) : <div className="text-sm text-ink-muted">No anomalies detected.</div>}
          </div>
        </Card>

        <Card>
          <SectionTitle right={<Link to="/students" className="chip">View all</Link>}>Top at-risk students</SectionTitle>
          <div className="space-y-1">
            {atRisk.data?.length ? atRisk.data.map((s) => (
              <Link key={s.student_id} to={`/students/${s.student_id}`} className="flex items-center justify-between rounded-lg px-2 py-1.5 text-sm transition-colors hover:bg-surface-50">
                <span className="text-ink-soft"><span className="font-medium text-ink">{s.student_id}</span> · {s.name}</span>
                <span className="font-semibold text-risk-high">{Math.round(s.risk_probability * 100)}%</span>
              </Link>
            )) : <div className="text-sm text-ink-muted">No predictions.</div>}
          </div>
        </Card>
      </div>

      <Card className="mt-4">
        <SectionTitle right={<span className="chip"><Sparkles className="h-3.5 w-3.5" /> AI</span>}>AI-generated insights</SectionTitle>
        <ul className="grid gap-2.5 md:grid-cols-2">
          {data.ai_insights.map((t, i) => (
            <li key={i} className="flex gap-2.5 rounded-xl bg-surface-50 px-3.5 py-3 text-sm text-ink-soft">
              <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-brand-500" />{t}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
