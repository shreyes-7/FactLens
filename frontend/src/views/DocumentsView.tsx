import { useEffect, useState } from "react";
import { FileText, Upload, Play, Info, Search, RefreshCw } from "lucide-react";
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

interface DocumentsViewProps {
  onOpenUpload: () => void;
  datasetId?: string;
  onRefreshCounts?: () => void;
  refreshTrigger?: number;
  onStartProcess?: (options: {
    documentId: string;
    filename: string;
    maxPages: number;
  }) => void;
}

export function DocumentsView({
  onOpenUpload,
  datasetId,
  onRefreshCounts,
  refreshTrigger,
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
  } | null>(null);

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
                      <ProcessingStatusBadge status={doc.status} />
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
          onStartProcess={onStartProcess}
          onProcessSuccess={() => {
            fetchDocs();
            if (onRefreshCounts) onRefreshCounts();
          }}
        />
      )}
    </div>
  );
}
