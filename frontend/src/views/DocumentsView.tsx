import { useEffect, useState } from "react";
import { FileText, Upload, Play, Info, Search, RefreshCw, Loader2, RotateCcw } from "lucide-react";
import { api } from "@/api/client";
import { DocumentResponse } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProcessingStatusBadge } from "@/components/shared/StatusBadge";
import { formatBytes, formatDate } from "@/lib/formatters";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { DocumentDetailDrawer } from "@/components/documents/DocumentDetailDrawer";
import { ProcessOptionsModal } from "@/components/documents/ProcessOptionsModal";
import { ActiveTask } from "@/components/shared/ActiveTaskBanner";

interface DocumentsViewProps {
  onOpenUpload: () => void;
  datasetId?: string;
  onRefreshCounts?: () => void;
  refreshTrigger?: number;
  activeTask?: ActiveTask | null;
  onStartProcess?: (options: {
    documentId: string;
    filename: string;
    maxPages: number;
    force?: boolean;
  }) => void;
}

export function DocumentsView({
  onOpenUpload,
  datasetId,
  onRefreshCounts,
  refreshTrigger,
  activeTask,
  onStartProcess,
}: DocumentsViewProps) {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);

  // Process modal state
  const [processModalDoc, setProcessModalDoc] = useState<{
    id: string;
    filename: string;
    pageCount: number;
    force?: boolean;
  } | null>(null);
  const [resettingId, setResettingId] = useState<string | null>(null);

  const fetchDocs = () => {
    setLoading(true);
    api.getDocuments(datasetId)
      .then(setDocuments)
      .catch((err) => console.error("Failed to load documents:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDocs();
  }, [datasetId, refreshTrigger]);

  // When active task completes, re-fetch documents to show updated status and counts
  useEffect(() => {
    if (activeTask?.status === "completed") {
      fetchDocs();
    }
  }, [activeTask?.status]);

  // Active status polling while any document is in processing or pending status or active task is running
  useEffect(() => {
    const hasActiveProcessing =
      (activeTask && activeTask.status === "running") ||
      documents.some((d) => {
        const s = (d.status || "").toLowerCase();
        return s === "processing" || s === "pending" || s === "queued";
      });

    const pollInterval = hasActiveProcessing ? 2000 : 8000;

    const timer = setInterval(() => {
      api.getDocuments(datasetId)
        .then((latestDocs) => {
          setDocuments(latestDocs);
          const stillProcessing = latestDocs.some((d) => {
            const s = (d.status || "").toLowerCase();
            return s === "processing" || s === "pending" || s === "queued";
          });
          // When all documents finish processing, refresh counts across app
          if (hasActiveProcessing && !stillProcessing && onRefreshCounts) {
            onRefreshCounts();
          }
        })
        .catch((err) => console.warn("Poll documents error:", err));
    }, pollInterval);

    return () => clearInterval(timer);
  }, [documents, datasetId, onRefreshCounts, activeTask]);

  const filteredDocs = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      {/* Top action bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-foreground">Document Management Hub</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Ingest financial reports, inspect page breakdowns, and trigger fact extraction.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchDocs} className="h-8 text-xs">
            <RefreshCw className="h-3 w-3 mr-1" />
            Refresh
          </Button>
          <Button size="sm" onClick={onOpenUpload} className="h-8 text-xs font-semibold shadow-sm">
            <Upload className="h-3.5 w-3.5 mr-1.5" />
            Upload PDF
          </Button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2 max-w-sm">
        <div className="relative w-full">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Filter documents by filename..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-8 h-8 text-xs bg-card"
          />
        </div>
      </div>

      {/* Documents Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-4 space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : filteredDocs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/40 border-b border-border/60 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Document</th>
                  <th className="py-3 px-4">Pages</th>
                  <th className="py-3 px-4">Size</th>
                  <th className="py-3 px-4">Uploaded</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {filteredDocs.map((doc) => (
                  <tr
                    key={doc.id}
                    onClick={() => setSelectedDocId(doc.id)}
                    className="hover:bg-muted/30 cursor-pointer transition-colors"
                  >
                    <td className="py-3 px-4 font-medium text-foreground">
                      <div className="flex items-center gap-2.5">
                        <FileText className="h-4 w-4 text-primary shrink-0" />
                        <span className="truncate max-w-xs sm:max-w-md font-semibold text-xs" title={doc.filename}>
                          {doc.filename}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono text-muted-foreground">
                      {doc.page_count} pages
                    </td>
                    <td className="py-3 px-4 font-mono text-muted-foreground">
                      {formatBytes(doc.file_size_bytes)}
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">
                      {formatDate(doc.created_at)}
                    </td>
                    <td className="py-3 px-4">
                      <ProcessingStatusBadge
                        status={
                          activeTask?.id === doc.id && activeTask.status === "running"
                            ? "processing"
                            : doc.status
                        }
                      />
                    </td>
                    <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedDocId(doc.id)}
                          className="h-7 text-xs text-muted-foreground hover:text-foreground"
                          title="View Details"
                        >
                          <Info className="h-3.5 w-3.5 mr-1" />
                          Details
                        </Button>
                        {(doc.status || "").toLowerCase() === "processing" ||
                        (activeTask?.id === doc.id && activeTask.status === "running") ? (
                          activeTask?.id === doc.id && activeTask.status === "running" ? (
                            <Button
                              variant="outline"
                              size="sm"
                              disabled
                              className="h-7 text-xs font-medium border-amber-500/30 text-amber-600 dark:text-amber-400 bg-amber-500/10 cursor-not-allowed"
                            >
                              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                              Extracting...
                            </Button>
                          ) : (
                            <div className="flex items-center gap-1.5">
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={resettingId === doc.id}
                                onClick={async () => {
                                  setResettingId(doc.id);
                                  try {
                                    await api.resetDocumentProcessing(doc.id);
                                    await fetchDocs();
                                    if (onRefreshCounts) onRefreshCounts();
                                  } catch (err) {
                                    console.error("Failed to reset document processing:", err);
                                  } finally {
                                    setResettingId(null);
                                  }
                                }}
                                className="h-7 text-xs font-medium border-rose-500/30 text-rose-500 hover:bg-rose-500/10"
                                title="Reset stuck processing status"
                              >
                                {resettingId === doc.id ? (
                                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                ) : (
                                  <RotateCcw className="h-3 w-3 mr-1" />
                                )}
                                Reset
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  setProcessModalDoc({
                                    id: doc.id,
                                    filename: doc.filename,
                                    pageCount: doc.page_count,
                                    force: true,
                                  })
                                }
                                className="h-7 text-xs font-medium border-primary/30 text-primary hover:bg-primary/10"
                                title="Force re-extraction"
                              >
                                <Play className="h-3 w-3 mr-1 fill-primary" />
                                Retry
                              </Button>
                            </div>
                          )
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              setProcessModalDoc({
                                id: doc.id,
                                filename: doc.filename,
                                pageCount: doc.page_count,
                              })
                            }
                            className="h-7 text-xs font-medium border-primary/30 text-primary hover:bg-primary/10"
                          >
                            <Play className="h-3 w-3 mr-1 fill-primary" />
                            Extract Facts
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No Documents Found"
            description={
              searchTerm
                ? "No documents match your filter term."
                : "Your document workspace is empty. Upload your first PDF to begin extracting grounded facts."
            }
            actionLabel={searchTerm ? undefined : "Upload First PDF"}
            onAction={onOpenUpload}
          />
        )}
      </div>

      {/* Document Detail Drawer */}
      <DocumentDetailDrawer
        documentId={selectedDocId}
        onClose={() => setSelectedDocId(null)}
        onTriggerProcess={(id, filename, pageCount) =>
          setProcessModalDoc({ id, filename, pageCount })
        }
      />

      {/* Extract Facts Options Modal */}
      {processModalDoc && (
        <ProcessOptionsModal
          isOpen={!!processModalDoc}
          onClose={() => setProcessModalDoc(null)}
          documentId={processModalDoc.id}
          filename={processModalDoc.filename}
          pageCount={processModalDoc.pageCount}
          onStartProcess={(options) => {
            // Optimistically update document status in UI
            setDocuments((prev) =>
              prev.map((d) => (d.id === options.documentId ? { ...d, status: "processing" } : d))
            );
            if (onStartProcess) {
              onStartProcess({
                ...options,
                force: processModalDoc.force || false,
              });
            }
          }}
          onProcessSuccess={() => {
            fetchDocs();
            if (onRefreshCounts) onRefreshCounts();
          }}
        />
      )}
    </div>
  );
}
