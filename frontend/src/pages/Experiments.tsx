import { useQuery } from "@tanstack/react-query";
import { listExperiments } from "@/lib/api";
import { PageHeader, Card, SectionTitle, Loading, ErrorState } from "@/components/ui";

export default function Experiments() {
  const q = useQuery({ queryKey: ["experiments"], queryFn: listExperiments });
  if (q.isLoading) return <Loading />;
  if (q.isError || !q.data) return <ErrorState />;

  return (
    <div>
      <PageHeader title="Experiment Tracking" subtitle="Every training run: model, feature set, metrics, seed." />
      <Card>
        <SectionTitle>{q.data.length} experiments</SectionTitle>
        {!q.data.length ? <div className="text-sm text-ink-muted">No experiments. Run scripts/train.py.</div> : (
          <table className="w-full">
            <thead><tr><th className="th">Name</th><th className="th">Model</th><th className="th">Features</th><th className="th">F1</th><th className="th">ROC-AUC</th><th className="th">HIGH recall</th><th className="th">When</th></tr></thead>
            <tbody>
              {q.data.map((e) => (
                <tr key={e.id} className="border-t border-surface-100">
                  <td className="td font-medium">{e.name}</td>
                  <td className="td">{e.model_type}</td>
                  <td className="td text-ink-muted">{e.feature_set}</td>
                  <td className="td">{e.metrics_summary?.f1_macro?.toFixed(3) ?? "—"}</td>
                  <td className="td">{e.metrics_summary?.roc_auc_ovr_macro?.toFixed(3) ?? "—"}</td>
                  <td className="td">{e.metrics_summary?.high_recall?.toFixed(3) ?? "—"}</td>
                  <td className="td text-xs text-ink-muted">{new Date(e.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
