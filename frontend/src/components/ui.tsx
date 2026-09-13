import { type ReactNode } from "react";
import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4 animate-fade-up">
      <div>
        <h1 className="text-2xl font-bold text-ink">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-ink-muted">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export function Card({ className, hover, children }: { className?: string; hover?: boolean; children: ReactNode }) {
  return <div className={cn("card card-pad", hover && "card-hover", className)}>{children}</div>;
}

export function SectionTitle({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <h2 className="text-sm font-bold text-ink">{children}</h2>
      {right}
    </div>
  );
}

export function StatCard({ label, value, sub, icon: Icon, accent = "brand", trend }: {
  label: string; value: ReactNode; sub?: ReactNode; icon?: LucideIcon;
  accent?: "brand" | "violet" | "emerald" | "amber" | "red"; trend?: { dir: "up" | "down"; text: string };
}) {
  const chip: Record<string, string> = {
    brand: "bg-brand-50 text-brand-600",
    violet: "bg-violet-500/10 text-violet-600",
    emerald: "bg-emerald-50 text-emerald-600",
    amber: "bg-amber-50 text-amber-600",
    red: "bg-red-50 text-red-600",
  };
  return (
    <div className="card card-hover card-pad animate-fade-up">
      <div className="flex items-start justify-between">
        <div className="stat-label">{label}</div>
        {Icon && <span className={cn("flex h-9 w-9 items-center justify-center rounded-xl", chip[accent])}><Icon className="h-5 w-5" strokeWidth={2.2} /></span>}
      </div>
      <div className="stat-value mt-2">{value}</div>
      {(sub || trend) && (
        <div className="mt-1 flex items-center gap-2 text-xs text-ink-muted">
          {trend && <span className={cn("font-semibold", trend.dir === "up" ? "text-emerald-600" : "text-red-600")}>{trend.dir === "up" ? "▲" : "▼"} {trend.text}</span>}
          {sub}
        </div>
      )}
    </div>
  );
}

const RISK_STYLES: Record<string, string> = {
  LOW_RISK: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/60",
  MEDIUM_RISK: "bg-amber-50 text-amber-700 ring-1 ring-amber-200/60",
  HIGH_RISK: "bg-red-50 text-red-700 ring-1 ring-red-200/60",
};
export function RiskBadge({ level }: { level: string }) {
  const label = level?.replace("_", " ").toLowerCase() ?? "—";
  return <span className={cn("badge capitalize", RISK_STYLES[level] || "bg-surface-100 text-ink-soft")}>{label}</span>;
}

export function SeverityDot({ severity }: { severity: string }) {
  const c = severity === "high" ? "bg-risk-high" : severity === "medium" ? "bg-risk-medium" : "bg-risk-low";
  return <span className={cn("inline-block h-2 w-2 rounded-full ring-4", c, severity === "high" ? "ring-red-100" : severity === "medium" ? "ring-amber-100" : "ring-emerald-100")} />;
}

export function ProgressBar({ value, max = 100, tone = "brand" }: { value: number; max?: number; tone?: "brand" | "risk" }) {
  const pct = Math.max(2, Math.min(100, (value / max) * 100));
  const color = tone === "risk"
    ? (pct < 50 ? "bg-risk-high" : pct < 70 ? "bg-risk-medium" : "bg-risk-low")
    : "bg-brand-grad";
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-surface-200">
      <div className={cn("h-full rounded-full transition-all duration-500", color)} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-ink-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-200 border-t-brand-600" />
      {label}
    </div>
  );
}

export function ErrorState({ message }: { message?: string }) {
  return <div className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">{message || "Something went wrong loading this data."}</div>;
}

export function EmptyState({ message }: { message: string }) {
  return <div className="flex items-center justify-center rounded-xl border border-dashed border-surface-300 py-10 text-sm text-ink-muted">{message}</div>;
}

export function ComingSoon({ phase, feature }: { phase: string; feature: string }) {
  return (
    <div className="card card-pad flex flex-col items-center justify-center py-16 text-center">
      <div className="text-sm font-medium text-ink-soft">{feature}</div>
      <p className="mt-1 max-w-md text-sm text-ink-muted">Delivered in {phase}.</p>
    </div>
  );
}

// Validated, colorblind-safe palette (data-viz skill reference instance).
export const CHART = {
  brand: "#4f46e5",
  blue: "#2a78d6",
  aqua: "#1baf7a",
  violet: "#4a3aa7",
  low: "#059669",
  medium: "#d97706",
  high: "#e1152f",
  grid: "#e9edf3",
  axis: "#98a2b3",
  series: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7"],
};

// Shared Recharts tooltip — a clean white card.
export function ChartTooltip({ active, payload, label, unit = "" }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-surface-200 bg-white/95 px-3 py-2 shadow-lift backdrop-blur">
      {label !== undefined && <div className="mb-1 text-[11px] font-semibold text-ink-muted">{label}</div>}
      {payload.map((p: any, i: number) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color || p.fill }} />
          <span className="text-ink-soft">{p.name}</span>
          <span className="ml-auto font-semibold text-ink">{p.value}{unit}</span>
        </div>
      ))}
    </div>
  );
}
