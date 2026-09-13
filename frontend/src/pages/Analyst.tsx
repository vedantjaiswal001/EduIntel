import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { askAnalyst, type AnalystAnswer } from "@/lib/api";
import { PageHeader, Card, SectionTitle, Loading } from "@/components/ui";

const EXAMPLES = [
  "Why are students performing poorly in Dynamic Programming?",
  "How healthy is the Algorithms course?",
  "Explain the risk for student S0004",
];

export default function Analyst() {
  const [q, setQ] = useState("");
  const m = useMutation<AnalystAnswer, Error, string>({ mutationFn: (question) => askAnalyst(question) });

  const submit = (question: string) => { setQ(question); if (question.trim()) m.mutate(question); };

  return (
    <div>
      <PageHeader title="AI Education Analyst" subtitle="Grounded, cited answers combining statistics, feedback and course documents." />
      <Card>
        <form onSubmit={(e) => { e.preventDefault(); submit(q); }} className="flex gap-2">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask about a course, topic, or student…"
            className="input flex-1" />
          <button className="btn-primary" type="submit">Ask</button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLES.map((e) => (
            <button key={e} onClick={() => submit(e)} className="rounded-full border border-surface-200 bg-white px-3 py-1.5 text-xs font-medium text-ink-soft transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700">{e}</button>
          ))}
        </div>
      </Card>

      {m.isPending && <Card className="mt-4"><Loading label="Analyzing evidence…" /></Card>}
      {m.isError && <Card className="mt-4"><div className="text-sm text-red-600">Query failed.</div></Card>}
      {m.data && (
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <SectionTitle right={<span className="badge bg-surface-100 text-ink-muted">{m.data.mode}</span>}>Answer</SectionTitle>
            {!m.data.sufficient && <div className="mb-2 rounded bg-amber-50 px-3 py-2 text-xs text-amber-700">Insufficient evidence — the analyst declined to speculate.</div>}
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink-soft">{m.data.answer}</pre>
            {m.data.citations.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {m.data.citations.map((c) => <span key={c} className="badge bg-brand-50 text-brand-700">{c}</span>)}
              </div>
            )}
          </Card>
          <Card>
            <SectionTitle>Evidence used</SectionTitle>
            <div className="space-y-2">
              {m.data.evidence.map((e, i) => (
                <div key={i} className="text-xs">
                  <span className="badge bg-surface-100 capitalize text-ink-muted">{e.kind}</span>
                  <div className="mt-0.5 text-ink-soft">{e.statement}</div>
                  <div className="text-ink-faint">source: {e.source}</div>
                </div>
              ))}
              {!m.data.evidence.length && <div className="text-sm text-ink-muted">No evidence.</div>}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
