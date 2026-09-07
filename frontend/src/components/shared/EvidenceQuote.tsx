import { FileText, Sparkles } from "lucide-react";
import { formatConfidence } from "@/lib/formatters";

export function EvidenceQuote({
  quote,
  documentFilename,
  pageNumber,
  printedPageNumber,
  confidenceScore,
  className = "",
}: {
  quote: string;
  documentFilename?: string | null;
  pageNumber?: number | null;
  printedPageNumber?: string | null;
  confidenceScore?: number | null;
  className?: string;
}) {
  return (
    <div
      className={`relative rounded-lg border border-border/80 bg-muted/30 p-3.5 text-xs text-foreground/90 transition-colors hover:border-primary/40 ${className}`}
    >
      <div className="flex items-center justify-between gap-2 pb-2 text-[11px] text-muted-foreground border-b border-border/40">
        <div className="flex items-center gap-1.5 font-medium truncate">
          <FileText className="h-3.5 w-3.5 text-primary/70 shrink-0" />
          <span className="truncate max-w-[220px]" title={documentFilename || "Document"}>
            {documentFilename || "Document"}
          </span>
          {(pageNumber || printedPageNumber) && (
            <span className="ml-1 rounded bg-secondary px-1.5 py-0.5 text-[10px] font-mono text-secondary-foreground">
              p. {printedPageNumber || pageNumber}
            </span>
          )}
        </div>
        {confidenceScore !== undefined && confidenceScore !== null && (
          <div className="flex items-center gap-1 text-[10px] text-emerald-500 font-mono shrink-0">
            <Sparkles className="h-3 w-3" />
            <span>{formatConfidence(confidenceScore)}</span>
          </div>
        )}
      </div>

      <blockquote className="mt-2.5 font-mono text-[11px] leading-relaxed text-foreground/80 italic border-l-2 border-primary/50 pl-2.5">
        "{quote}"
      </blockquote>
    </div>
  );
}
