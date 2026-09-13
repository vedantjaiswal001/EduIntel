import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getTopicPerf, getTopicStudents } from "@/lib/api";
import { PageHeader, Card, SectionTitle, StatCard, Loading, ErrorState, ProgressBar } from "@/components/ui";

export default function TopicDetail() {
  const { id = "" } = useParams();
  const perf = useQuery({ queryKey: ["tperf", id], queryFn: () => getTopicPerf(id) });
  const students = useQuery({ queryKey: ["tstudents", id], queryFn: () => getTopicStudents(id) });

  if (perf.isLoading) return <Loading />;
  if (perf.isError || !perf.data) return <ErrorState message="Topic not found." />;
  const p = perf.data;

  return (
    <div>
      <PageHeader title={p.name} subtitle={`Course ${p.course_id} · difficulty ${p.difficulty}`}
        actions={<Link to="/topics" className="text-sm text-brand-600">← Topics</Link>} />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Mean mastery" value={p.mean_mastery_pct != null ? `${p.mean_mastery_pct}%` : "—"} />
        <StatCard label="Students" value={p.students} />
        <StatCard label="Difficulty" value={p.difficulty} />
        <StatCard label="Status" value={p.is_weak ? "Weak" : "OK"} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle>Mastery distribution</SectionTitle>
          {p.distribution && Object.entries(p.distribution).map(([bucket, n]) => (
            <div key={bucket} className="mb-2 flex items-center gap-2 text-sm">
              <span className="w-16 text-ink-muted">{bucket}%</span>
              <div className="flex-1"><ProgressBar value={(n as number)} max={p.students} /></div>
              <span className="w-8 text-right text-ink-soft">{n as number}</span>
            </div>
          ))}
        </Card>
        <Card>
          <SectionTitle>Lowest-mastery students</SectionTitle>
          {students.isLoading ? <Loading /> : students.isError ? <ErrorState /> : (
            <div className="max-h-80 overflow-y-auto">
              <table className="w-full">
                <thead><tr><th className="th">Student</th><th className="th">Mastery</th><th className="th">Assessments</th></tr></thead>
                <tbody>
                  {students.data!.slice(0, 30).map((s) => (
                    <tr key={s.student_id} className="border-t border-surface-100">
                      <td className="td"><Link to={`/students/${s.student_id}`} className="text-brand-600 hover:underline">{s.student_id}</Link></td>
                      <td className="td">{s.mastery_pct}%</td>
                      <td className="td text-ink-muted">{s.assessments}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
