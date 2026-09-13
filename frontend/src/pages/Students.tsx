import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listStudents, getAtRisk } from "@/lib/api";
import { PageHeader, Card, SectionTitle, Loading, ErrorState, RiskBadge } from "@/components/ui";

export default function Students() {
  const [search, setSearch] = useState("");
  const students = useQuery({ queryKey: ["students", search], queryFn: () => listStudents({ limit: 25, search: search || undefined }) });
  const atRisk = useQuery({ queryKey: ["atrisk", 15], queryFn: () => getAtRisk(15) });

  return (
    <div>
      <PageHeader title="Student 360" subtitle="Search students and triage by predicted risk." />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle right={<span className="text-xs text-red-600">highest first</span>}>At-risk students</SectionTitle>
          {atRisk.isLoading ? <Loading /> : atRisk.isError ? <ErrorState /> : (
            <table className="w-full">
              <thead><tr><th className="th">Student</th><th className="th">Risk</th><th className="th text-right">P(high)</th></tr></thead>
              <tbody>
                {atRisk.data!.map((s) => (
                  <tr key={s.student_id} className="border-t border-surface-100 hover:bg-surface-50">
                    <td className="td"><Link className="text-brand-600 hover:underline" to={`/students/${s.student_id}`}>{s.student_id}</Link> <span className="text-ink-muted">{s.name}</span></td>
                    <td className="td"><RiskBadge level={s.risk_label} /></td>
                    <td className="td text-right font-medium text-red-600">{Math.round(s.risk_probability * 100)}%</td>
                  </tr>
                ))}
                {!atRisk.data!.length && <tr><td className="td text-ink-muted" colSpan={3}>No predictions — run scripts/train.py.</td></tr>}
              </tbody>
            </table>
          )}
        </Card>

        <Card>
          <SectionTitle>Directory</SectionTitle>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or ID…"
            className="input mb-3"
          />
          {students.isLoading ? <Loading /> : students.isError ? <ErrorState /> : (
            <div className="max-h-96 overflow-y-auto">
              <table className="w-full">
                <thead><tr><th className="th">ID</th><th className="th">Name</th><th className="th">Program</th></tr></thead>
                <tbody>
                  {students.data!.items.map((s) => (
                    <tr key={s.id} className="border-t border-surface-100 hover:bg-surface-50">
                      <td className="td"><Link className="text-brand-600 hover:underline" to={`/students/${s.id}`}>{s.id}</Link></td>
                      <td className="td">{s.name}</td>
                      <td className="td text-ink-muted">{s.program}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="pt-2 text-xs text-ink-muted">{students.data!.total} students total</div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
