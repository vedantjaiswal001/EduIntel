import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { listDocuments, ragQuery, type RagResponse } from "@/lib/api";
import { PageHeader, Card, SectionTitle, Loading, ErrorState } from "@/components/ui";

export default function KnowledgeBase() {
  const docs = useQuery({ queryKey: ["documents"], queryFn: listDocuments });
  const [q, setQ] = useState("");
  const m = useMutation<RagResponse, Error, string>({ mutationFn: (query) => ragQuery({ query, top_k: 5 }) });

  return (
    <div>
      <PageHeader title="Knowledge Base" subtitle="Semantic search over ingested course material (pgvector)." />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <SectionTitle>Documents</SectionTitle>
          {docs.isLoading ? <Loading /> : docs.isError ? <ErrorState /> : (
            <div className="max-h-96 overflow-y-auto text-sm">
              {docs.data!.map((d) => (
                <div key={d.id} className="border-b border-surface-100 py-2">
                  <div className="font-medium text-ink">{d.title}</div>
                  <div className="text-xs text-ink-muted">{d.doc_type} · {d.num_chunks} chunks · {d.course_id ?? "—"}</div>
                </div>
              ))}
              {!docs.data!.length && <div className="text-ink-muted">No documents. Run scripts/ingest_docs.py.</div>}
            </div>
          )}
          {docs.data?.[0]?.embedding_method && <div className="mt-2 text-[11px] text-ink-faint">Embeddings: {docs.data[0].embedding_method}</div>}
        </Card>

        <Card className="lg:col-span-2">
          <SectionTitle>Semantic search</SectionTitle>
          <form onSubmit={(e) => { e.preventDefault(); if (q.trim()) m.mutate(q); }} className="flex gap-2">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. material explaining recursion and memoization"
              className="input flex-1" />
            <button className="btn-primary">Search</button>
          </form>
          {m.isPending && <Loading />}
          {m.data && (
            <div className="mt-3">
              {!m.data.sufficient && <div className="mb-2 rounded bg-amber-50 px-3 py-2 text-xs text-amber-700">No sufficiently relevant material found.</div>}
              {m.data.results.map((r) => (
                <div key={r.chunk_id} className="border-b border-surface-100 py-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-brand-700">{r.citation}</span>
                    <span className="text-xs text-ink-muted">sim {r.similarity.toFixed(2)}</span>
                  </div>
                  <div className="mt-1 text-sm text-ink-soft">{r.content.slice(0, 220)}…</div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
