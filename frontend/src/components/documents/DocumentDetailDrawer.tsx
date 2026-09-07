import { useEffect, useState } from "react";
import { FileText, Clock } from "lucide-react";
import { api } from "@/api/client";
import { DocumentDetailResponse, ProcessingRunItem } from "@/api/types";
import { Sheet } from "@/components/ui/dialog";
import { ProcessingStatusBadge } from "@/components/shared/StatusBadge";
import { formatBytes, formatDate } from "@/lib/formatters";
import { Skeleton } from "@/components/ui/skeleton";

interface DocumentDetailDrawerProps {
  documentId: string | null;
  onClose: () => void;
  onTriggerProcess: (docId: string, filename: string, pageCount: number) => void;
}

export function DocumentDetailDrawer({
  documentId,
  onClose,
  onTriggerProcess,
}: DocumentDetailDrawerProps) {
  const [doc, setDoc] = useState<DocumentDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!documentId) {
      setDoc(null);
      return;
    }
    setLoading(true);
    api.getDocumentDetail(documentId)
      .then(setDoc)
      .catch((err) => console.error("Error loading document detail:", err))
      .finally(() => setLoading(false));
  }, [documentId]);

  return (
    <Sheet
      isOpen={!!documentId}
      onClose={onClose}
      title="Document Details & Audit"
      description="Inspect page breakdown, vector chunk status, and extraction audit trail."
    >
      {loading ? (
        <div className="space-y-4 pt-2">
          <Skeleton className="h-6 w-3/4" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : doc ? (
        <div className="space-y-5 pt-2">
          {/* Header summary */}
          <div className="p-4 rounded-xl border border-border/80 bg-muted/20 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <div className="h-9 w-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground truncate max-w-sm" title={doc.filename}>
                    {doc.filename}
                  </h3>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Uploaded {formatDate(doc.created_at)}
                  </p>
                </div>
              </div>
              <ProcessingStatusBadge status={doc.status} />
            </div>

            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border/40 text-center">
              <div className="p-2 rounded bg-background/50 border border-border/40">
                <p className="text-[10px] text-muted-foreground uppercase font-semibold">Pages</p>
                <p className="text-base font-bold text-foreground font-mono">{doc.page_count}</p>
              </div>
              <div className="p-2 rounded bg-background/50 border border-border/40">
                <p className="text-[10px] text-muted-foreground uppercase font-semibold">Chunks</p>
                <p className="text-base font-bold text-foreground font-mono">{doc.total_chunks}</p>
              </div>
              <div className="p-2 rounded bg-background/50 border border-border/40">
                <p className="text-[10px] text-muted-foreground uppercase font-semibold">Facts</p>
                <p className="text-base font-bold text-emerald-500 font-mono">{doc.total_facts_extracted}</p>
              </div>
            </div>
          </div>

          {/* Storage & Technical metadata */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider">
              Technical Metadata
            </h4>
            <div className="rounded-lg border border-border/60 bg-muted/30 divide-y divide-border/40 text-xs">
              <div className="p-2.5 flex justify-between items-center">
                <span className="text-muted-foreground">Document ID</span>
                <span className="font-mono text-[10px] text-foreground/80">{doc.id}</span>
              </div>
              <div className="p-2.5 flex justify-between items-center">
                <span className="text-muted-foreground">File Size</span>
                <span className="font-mono text-foreground/80">{formatBytes(doc.file_size_bytes)}</span>
              </div>
              <div className="p-2.5 flex justify-between items-center">
                <span className="text-muted-foreground">Supabase Storage</span>
                <span className="font-mono text-[10px] text-foreground/80 truncate max-w-[240px]" title={doc.storage_path}>
                  {doc.storage_path}
                </span>
              </div>
            </div>
          </div>

          {/* Processing Runs Audit */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider">
              Processing History ({doc.processing_runs?.length || 0})
            </h4>
            {doc.processing_runs && doc.processing_runs.length > 0 ? (
              <div className="space-y-2">
                {doc.processing_runs.map((run: ProcessingRunItem) => (
                  <div
                    key={run.id}
                    className="p-3 rounded-lg border border-border/60 bg-muted/20 text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 font-medium">
                        <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                        <span>{formatDate(run.started_at)}</span>
                      </div>
                      <span
                        className={`px-1.5 py-0.2 rounded text-[10px] font-mono font-medium ${
                          run.status === "COMPLETED"
                            ? "bg-emerald-500/10 text-emerald-500"
                            : "bg-amber-500/10 text-amber-500"
                        }`}
                      >
                        {run.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-[11px] text-muted-foreground pt-1">
                      <span>Pages: <b className="text-foreground">{run.pages_processed}</b></span>
                      <span>Chunks: <b className="text-foreground">{run.chunks_created}</b></span>
                      <span>Facts: <b className="text-emerald-500">{run.facts_extracted}</b></span>
                      {run.facts_rejected > 0 && (
                        <span>Rejected: <b className="text-rose-500">{run.facts_rejected}</b></span>
                      )}
                    </div>
                    {run.error_message && (
                      <p className="text-[11px] text-rose-400 bg-rose-500/10 p-1.5 rounded mt-1 font-mono">
                        {run.error_message}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 rounded-lg border border-dashed border-border/60 text-center text-xs text-muted-foreground">
                No processing runs recorded yet.
              </div>
            )}
          </div>

          {/* Action to extract more */}
          <div className="pt-2">
            <button
              onClick={() => {
                onClose();
                onTriggerProcess(doc.id, doc.filename, doc.page_count);
              }}
              className="w-full py-2.5 px-4 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-semibold shadow-sm transition-all text-center"
            >
              Extract Facts from this Document
            </button>
          </div>
        </div>
      ) : null}
    </Sheet>
  );
}
