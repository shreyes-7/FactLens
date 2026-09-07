import { FileText, ShieldCheck, Quote, Clock, Layers, Sparkles } from "lucide-react";
import { FactWithEvidenceResponse } from "@/api/types";
import { Sheet } from "@/components/ui/dialog";
import { formatConfidence, formatNormalizedValue, formatDate } from "@/lib/formatters";

interface EvidenceInspectorProps {
  fact: FactWithEvidenceResponse | null;
  onClose: () => void;
}

export function EvidenceInspector({ fact, onClose }: EvidenceInspectorProps) {
  if (!fact) return null;

  return (
    <Sheet
      isOpen={!!fact}
      onClose={onClose}
      title="Evidence Grounding Inspector"
      description="Trace this extracted fact directly to its exact PDF page quotation and character spans."
    >
      <div className="space-y-5 pt-2">
        {/* Core Fact Card */}
        <div className="p-4 rounded-xl border border-border/80 bg-muted/20 space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                {fact.category || "NUMERICAL FACT"}
              </span>
              <h3 className="text-base font-bold text-foreground mt-2 tracking-tight">
                {fact.predicate}
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Entity: <b className="text-foreground">{fact.entity}</b>
              </p>
            </div>
            {fact.confidence_score !== undefined && fact.confidence_score !== null && (
              <div className="flex items-center gap-1 text-xs font-mono text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20">
                <Sparkles className="h-3 w-3" />
                <span>{formatConfidence(fact.confidence_score)}</span>
              </div>
            )}
          </div>

          {/* Value comparison strip */}
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border/40">
            <div className="p-2.5 rounded-lg bg-background/50 border border-border/40">
              <p className="text-[10px] text-muted-foreground uppercase font-semibold">Raw Claim</p>
              <p className="text-sm font-bold text-foreground font-mono mt-0.5">{fact.raw_value}</p>
            </div>
            <div className="p-2.5 rounded-lg bg-background/50 border border-border/40">
              <p className="text-[10px] text-muted-foreground uppercase font-semibold">Normalized Base Value</p>
              <p className="text-sm font-bold text-primary font-mono mt-0.5">
                {formatNormalizedValue(fact.normalized_value, fact.unit)}
              </p>
            </div>
          </div>

          {/* Context Pills */}
          <div className="flex flex-wrap gap-1.5 pt-1 text-[11px]">
            {fact.time_period && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border/50">
                <Clock className="h-3 w-3" />
                <span>{fact.time_period}</span>
              </span>
            )}
            {fact.scope && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border/50">
                <Layers className="h-3 w-3" />
                <span>Scope: {fact.scope}</span>
              </span>
            )}
            {fact.status && (
              <span className="px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border/50">
                Status: {fact.status}
              </span>
            )}
          </div>
        </div>

        {/* Source Grounding & Evidence Citations */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider flex items-center gap-1.5">
              <Quote className="h-3.5 w-3.5 text-primary" />
              Source Grounding Quotes ({fact.evidence?.length || 1})
            </h4>
            <span className="text-[10px] text-emerald-500 font-medium flex items-center gap-1">
              <ShieldCheck className="h-3 w-3" />
              Verified in PDF
            </span>
          </div>

          {fact.evidence && fact.evidence.length > 0 ? (
            <div className="space-y-2.5">
              {fact.evidence.map((ev, idx) => (
                <div
                  key={ev.id || idx}
                  className="p-3.5 rounded-xl border border-primary/20 bg-primary/5 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between text-[11px] text-muted-foreground border-b border-primary/10 pb-2">
                    <div className="flex items-center gap-1.5 font-medium truncate">
                      <FileText className="h-3.5 w-3.5 text-primary shrink-0" />
                      <span className="truncate max-w-[200px]" title={fact.document_filename || "PDF Document"}>
                        {fact.document_filename || "PDF Document"}
                      </span>
                      <span className="ml-1 rounded bg-primary/10 text-primary px-1.5 py-0.2 font-mono text-[10px]">
                        Page {ev.printed_page_number || ev.page_number || fact.page_number}
                      </span>
                    </div>
                    {ev.char_start !== null && ev.char_start !== undefined && (
                      <span className="font-mono text-[10px] text-muted-foreground">
                        Offset: [{ev.char_start}:{ev.char_end}]
                      </span>
                    )}
                  </div>

                  <blockquote className="font-mono text-xs leading-relaxed text-foreground italic pl-2.5 border-l-2 border-primary">
                    "{ev.quote}"
                  </blockquote>
                </div>
              ))}
            </div>
          ) : fact.quote ? (
            <div className="p-3.5 rounded-xl border border-primary/20 bg-primary/5 space-y-2 text-xs">
              <div className="flex items-center justify-between text-[11px] text-muted-foreground border-b border-primary/10 pb-2">
                <div className="flex items-center gap-1.5 font-medium truncate">
                  <FileText className="h-3.5 w-3.5 text-primary shrink-0" />
                  <span>{fact.document_filename || "PDF Document"}</span>
                  <span className="ml-1 rounded bg-primary/10 text-primary px-1.5 py-0.2 font-mono text-[10px]">
                    Page {fact.printed_page_number || fact.page_number}
                  </span>
                </div>
              </div>
              <blockquote className="font-mono text-xs leading-relaxed text-foreground italic pl-2.5 border-l-2 border-primary">
                "{fact.quote}"
              </blockquote>
            </div>
          ) : (
            <div className="p-4 rounded-lg border border-dashed border-border text-center text-xs text-muted-foreground">
              No evidence quote recorded for this fact.
            </div>
          )}
        </div>

        {/* Provenance Audit */}
        <div className="p-3 rounded-lg border border-border/60 bg-muted/20 text-[11px] space-y-1.5">
          <p className="font-semibold text-foreground/80">Extraction Provenance:</p>
          <div className="flex justify-between text-muted-foreground">
            <span>Fact UUID:</span>
            <span className="font-mono text-[10px] text-foreground/80">{fact.id}</span>
          </div>
          <div className="flex justify-between text-muted-foreground">
            <span>Extracted At:</span>
            <span className="font-mono text-[10px] text-foreground/80">{formatDate(fact.created_at)}</span>
          </div>
        </div>
      </div>
    </Sheet>
  );
}
