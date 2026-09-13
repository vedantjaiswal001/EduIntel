import { useQuery } from "@tanstack/react-query";
import { listModels, getModel } from "@/lib/api";
import { PageHeader, Card, SectionTitle, StatCard, Loading, ErrorState } from "@/components/ui";

export default function Models() {
  const models = useQuery({ queryKey: ["models"], queryFn: listModels });
  const active = models.data?.find((m) => m.status === "active");
  const detail = useQuery({ queryKey: ["model", active?.id], queryFn: () => getModel(active!.id), enabled: !!active });

  if (models.isLoading) return <Loading />;
  if (models.isError) return <ErrorState />;

  const m = detail.data?.metrics;
  const fn = m?.false_negative_analysis;
  const cm = m?.confusion_matrix;

  return (
    <div>
      <PageHeader title="ML Model Center" subtitle="Versioned models, metrics, calibration and false-negative analysis." />
      {!models.data?.length ? <Card><div className="text-sm text-ink-muted">No models. Run scripts/train.py.</div></Card> : (
        <>
          {active && (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <StatCard label="Active model" value={active.model_type} sub={active.version} />
              <StatCard label="Macro F1" value={active.metrics_summary.f1_macro?.toFixed(3) ?? "—"} />
              <StatCard label="ROC-AUC" value={active.metrics_summary.roc_auc_ovr_macro?.toFixed(3) ?? "—"} />
              <StatCard label="HIGH recall" value={active.metrics_summary.high_recall?.toFixed(3) ?? "—"} />
            </div>
          )}

          {fn && (
            <Card className="mt-4">
              <SectionTitle>False-negative analysis (HIGH risk)</SectionTitle>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4 text-sm">
                <div><div className="stat-label">HIGH students</div><div className="text-lg font-semibold">{fn.n_high_risk}</div></div>
                <div><div className="stat-label">HIGH recall</div><div className="text-lg font-semibold">{fn.high_recall?.toFixed(3)}</div></div>
                <div><div className="stat-label">False negatives</div><div className="text-lg font-semibold text-red-600">{fn.high_false_negatives}</div></div>
                <div><div className="stat-label">Missed as LOW</div><div className="text-lg font-semibold text-red-600">{fn.high_missed_as_low}</div></div>
              </div>
              <p className="mt-2 text-xs text-ink-muted">{fn.note}</p>
            </Card>
          )}

          {cm && (
            <Card className="mt-4">
              <SectionTitle>Confusion matrix (rows = actual, cols = predicted)</SectionTitle>
              <table className="text-sm">
                <thead><tr><th className="th"></th>{cm.labels.map((l: string) => <th key={l} className="th">{l.replace("_RISK", "")}</th>)}</tr></thead>
                <tbody>
                  {cm.matrix.map((row: number[], i: number) => (
                    <tr key={i}><td className="td font-medium">{cm.labels[i].replace("_RISK", "")}</td>
                      {row.map((v, j) => <td key={j} className={`td text-center ${i === j ? "font-semibold text-emerald-700" : "text-ink-soft"}`}>{v}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}

          <Card className="mt-4">
            <SectionTitle>Model versions</SectionTitle>
            <table className="w-full">
              <thead><tr><th className="th">Version</th><th className="th">Type</th><th className="th">Status</th><th className="th">F1</th><th className="th">ROC-AUC</th><th className="th">HIGH recall</th></tr></thead>
              <tbody>
                {models.data!.map((mv) => (
                  <tr key={mv.id} className="border-t border-surface-100">
                    <td className="td font-mono text-xs">{mv.version}</td>
                    <td className="td">{mv.model_type}</td>
                    <td className="td">{mv.status === "active" ? <span className="badge bg-emerald-50 text-emerald-700">active</span> : mv.status}</td>
                    <td className="td">{mv.metrics_summary.f1_macro?.toFixed(3) ?? "—"}</td>
                    <td className="td">{mv.metrics_summary.roc_auc_ovr_macro?.toFixed(3) ?? "—"}</td>
                    <td className="td">{mv.metrics_summary.high_recall?.toFixed(3) ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
  );
}
