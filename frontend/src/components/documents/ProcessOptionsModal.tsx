import { useState } from "react";
import { Play, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { api } from "@/api/client";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface ProcessOptionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentId: string;
  filename: string;
  pageCount: number;
  onProcessSuccess?: () => void;
  onStartProcess?: (options: {
    documentId: string;
    filename: string;
    maxPages: number;
  }) => void;
}

export function ProcessOptionsModal({
  isOpen,
  onClose,
  documentId,
  filename,
  pageCount,
  onProcessSuccess,
  onStartProcess,
}: ProcessOptionsModalProps) {
  const [maxPages, setMaxPages] = useState<number>(5);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successInfo, setSuccessInfo] = useState<string | null>(null);

  const handleStartProcessing = async () => {
    // If caller provided onStartProcess, immediately close dialog and delegate to background task
    if (onStartProcess) {
      onStartProcess({
        documentId,
        filename,
        maxPages,
      });
      onClose();
      return;
    }

    setIsProcessing(true);
    setError(null);
    try {
      const resp = await api.processDocument(
        documentId,
        {
          max_pages: maxPages,
          page_offset: 0,
          chunk_size: 800,
          chunk_overlap: 100,
        },
        false // synchronous execution so user sees facts extracted immediately
      );
      setSuccessInfo(
        `Extracted ${resp.facts_extracted} grounded facts across ${resp.chunks_created} chunks.`
      );
      setTimeout(() => {
        setIsProcessing(false);
        setSuccessInfo(null);
        if (onProcessSuccess) onProcessSuccess();
        onClose();
      }, 1500);
    } catch (err: any) {
      setIsProcessing(false);
      setError(err.message || "Failed to process document.");
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Extract Facts & Ground Evidence"
      description={`Run the chunking, embedding, LLM extraction, and evidence grounding pipeline for '${filename}'.`}
    >
      <div className="space-y-4 pt-2">
        {/* Page selection */}
        <div>
          <label className="text-xs font-semibold text-foreground/90 block mb-1.5">
            Pages to Process (Total: {pageCount} pages available)
          </label>
          <div className="grid grid-cols-4 gap-2">
            {[3, 5, 10, pageCount].map((pages) => (
              <button
                key={pages}
                type="button"
                onClick={() => setMaxPages(pages)}
                className={`py-2 px-3 rounded-lg border text-xs font-medium transition-all ${
                  maxPages === pages
                    ? "border-primary bg-primary/10 text-primary font-semibold shadow-sm"
                    : "border-border hover:bg-muted text-muted-foreground"
                }`}
              >
                {pages === pageCount ? `All (${pages})` : `${pages} pages`}
              </button>
            ))}
          </div>
          <p className="text-[11px] text-muted-foreground mt-1.5">
            Processing 3–5 pages completes in ~8 seconds; larger batches run with rate-limit handling.
          </p>
        </div>

        {/* Pipeline steps overview */}
        <div className="p-3 rounded-lg border border-border/60 bg-muted/30 text-[11px] space-y-1.5">
          <p className="font-semibold text-foreground/80">Pipeline Execution Steps:</p>
          <ul className="list-disc list-inside space-y-0.5 text-muted-foreground">
            <li>Page text boundary-preserved chunking (800 chars, 100 overlap)</li>
            <li>1024-d Jina semantic vector embedding generation & pgvector storage</li>
            <li>Gemini 2.5 Flash atomic fact extraction (Groq auto-fallback)</li>
            <li>Character offset validation against raw PDF text</li>
          </ul>
        </div>

        {/* Alerts */}
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-500 text-xs">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successInfo && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-500 text-xs">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{successInfo}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-2">
          <Button variant="outline" size="sm" onClick={onClose} disabled={isProcessing}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleStartProcessing}
            disabled={isProcessing}
            className="shadow-sm"
          >
            {isProcessing ? (
              <>
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                Extracting Facts...
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 mr-1.5 fill-current" />
                Start Extraction
              </>
            )}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
