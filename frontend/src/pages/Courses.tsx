import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listCourses, getCourseHealth, type CourseHealth } from "@/lib/api";
import { PageHeader, Card, Loading, ErrorState, ProgressBar } from "@/components/ui";

export default function Courses() {
  const q = useQuery({
    queryKey: ["courses-health"],
    queryFn: async () => {
      const courses = await listCourses();
      const healths = await Promise.all(courses.map((c) => getCourseHealth(c.id).catch(() => null)));
      return courses.map((c, i) => ({ course: c, health: healths[i] as CourseHealth | null }))
        .sort((a, b) => (a.health?.score ?? 999) - (b.health?.score ?? 999));
    },
  });

  if (q.isLoading) return <Loading />;
  if (q.isError || !q.data) return <ErrorState />;

  return (
    <div>
      <PageHeader title="Course Intelligence" subtitle="Course-health scores (lowest first) with transparent components." />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {q.data.map(({ course, health }) => (
          <Link key={course.id} to={`/courses/${course.id}`}>
            <Card className="h-full transition-shadow hover:shadow-md">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-sm font-semibold text-ink">{course.title}</div>
                  <div className="text-xs text-ink-muted">{course.code} · {course.instructor_name}</div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-semibold text-ink">{health?.score ?? "—"}</div>
                  <div className="text-[10px] uppercase tracking-wide text-ink-faint">health</div>
                </div>
              </div>
              {health && <div className="mt-3"><ProgressBar value={health.score ?? 0} tone="risk" /></div>}
              {health && (
                <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-ink-muted">
                  {Object.entries(health.components).map(([k, v]) => (
                    <div key={k} className="flex justify-between"><span className="capitalize">{k.replace("_", " ")}</span><span className="text-ink-soft">{v ?? "—"}</span></div>
                  ))}
                </div>
              )}
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
