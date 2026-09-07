import { FileText, ArrowRightLeft, Sparkles } from "lucide-react";
import { RelationshipWithDetailsResponse } from "@/api/types";
import { RelationshipBadge } from "@/components/shared/StatusBadge";
import { formatNormalizedValue, formatConfidence } from "@/lib/formatters";

interface ComparisonCardProps {
  relationship: RelationshipWithDetailsResponse;
  onInspectFact?: (factId: string) => void;
}

export function ComparisonCard({ relationship, onInspectFact }: ComparisonCardProps) {
  const { fact_a, fact_b, relationship_type, confidence, rationale, contextual_factors, evidence_a_quote, evidence_b_quote } = relationship;

  // Determine accent border based on relationship type
  const getBorderClass = () => {
    switch (relationship_type) {
      case "CORROBORATES":
        return "border-emerald-500/30 hover:border-emerald-500/50 bg-emerald-500/[0.02]";
      case "CONTRADICTS":
        return "border-rose-500/30 hover:border-rose-500/50 bg-rose-500/[0.02]";
      case "CONTEXTUAL_DIFFERENCE":
        return "border-amber-500/30 hover:border-amber-500/50 bg-amber-500/[0.02]";
      case "RELATED":
        return "border-sky-500/30 hover:border-sky-500/50 bg-sky-500/[0.02]";
      default:
        return "border-border hover:border-muted-foreground/40 bg-card";
    }
  };

  return (
    <div className={`rounded-xl border p-5 transition-all shadow-sm space-y-4 ${getBorderClass()}`}>
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <RelationshipBadge type={relationship_type} />
          <span className="text-xs font-mono text-muted-foreground">
            Pair ID: {relationship.id.slice(0, 8)}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs font-mono font-medium text-foreground/80 bg-muted/50 px-2 py-0.5 rounded border border-border/50">
          <Sparkles className="h-3 w-3 text-primary" />
          <span>Confidence: {formatConfidence(confidence)}</span>
        </div>
      </div>

      {/* Side-by-Side Facts Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch">
        {/* Fact A */}
        <div
          onClick={() => onInspectFact && onInspectFact(fact_a.id)}
          className="rounded-lg border border-border/70 bg-card/60 p-4 space-y-2 cursor-pointer hover:border-primary/40 transition-colors flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center justify-between text-[11px] text-muted-foreground border-b border-border/40 pb-2">
              <span className="flex items-center gap-1 font-medium truncate max-w-[180px]" title={fact_a.document_filename || "Document A"}>
                <FileText className="h-3.5 w-3.5 text-primary/70 shrink-0" />
                {fact_a.document_filename || "Document A"}
              </span>
              {fact_a.page_number && (
                <span className="font-mono text-[10px] bg-muted px-1.5 py-0.2 rounded">
                  Page {fact_a.page_number}
                </span>
              )}
            </div>

            <div className="pt-2">
              <h4 className="text-xs font-semibold text-foreground">{fact_a.predicate}</h4>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-sm font-bold font-mono text-foreground">{fact_a.raw_value}</span>
                {fact_a.normalized_value !== null && fact_a.normalized_value !== undefined && (
                  <span className="text-xs font-mono text-muted-foreground">
                    ({formatNormalizedValue(fact_a.normalized_value, fact_a.unit)})
                  </span>
                )}
              </div>
            </div>

            <div className="flex flex-wrap gap-1.5 pt-2 text-[10px] text-muted-foreground">
              {fact_a.time_period && <span className="px-1.5 py-0.5 rounded bg-muted">Period: {fact_a.time_period}</span>}
              {fact_a.scope && <span className="px-1.5 py-0.5 rounded bg-muted">Scope: {fact_a.scope}</span>}
            </div>
          </div>

          {/* Evidence quote */}
          {(evidence_a_quote || fact_a.quote) && (
            <blockquote className="mt-3 p-2 rounded bg-muted/40 font-mono text-[11px] text-foreground/80 italic border-l-2 border-primary/50">
              "{evidence_a_quote || fact_a.quote}"
            </blockquote>
          )}
        </div>

        {/* Fact B */}
        <div
          onClick={() => onInspectFact && onInspectFact(fact_b.id)}
          className="rounded-lg border border-border/70 bg-card/60 p-4 space-y-2 cursor-pointer hover:border-primary/40 transition-colors flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center justify-between text-[11px] text-muted-foreground border-b border-border/40 pb-2">
              <span className="flex items-center gap-1 font-medium truncate max-w-[180px]" title={fact_b.document_filename || "Document B"}>
                <FileText className="h-3.5 w-3.5 text-primary/70 shrink-0" />
                {fact_b.document_filename || "Document B"}
              </span>
              {fact_b.page_number && (
                <span className="font-mono text-[10px] bg-muted px-1.5 py-0.2 rounded">
                  Page {fact_b.page_number}
                </span>
              )}
            </div>

            <div className="pt-2">
              <h4 className="text-xs font-semibold text-foreground">{fact_b.predicate}</h4>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-sm font-bold font-mono text-foreground">{fact_b.raw_value}</span>
                {fact_b.normalized_value !== null && fact_b.normalized_value !== undefined && (
                  <span className="text-xs font-mono text-muted-foreground">
                    ({formatNormalizedValue(fact_b.normalized_value, fact_b.unit)})
                  </span>
                )}
              </div>
            </div>

            <div className="flex flex-wrap gap-1.5 pt-2 text-[10px] text-muted-foreground">
              {fact_b.time_period && <span className="px-1.5 py-0.5 rounded bg-muted">Period: {fact_b.time_period}</span>}
              {fact_b.scope && <span className="px-1.5 py-0.5 rounded bg-muted">Scope: {fact_b.scope}</span>}
            </div>
          </div>

          {/* Evidence quote */}
          {(evidence_b_quote || fact_b.quote) && (
            <blockquote className="mt-3 p-2 rounded bg-muted/40 font-mono text-[11px] text-foreground/80 italic border-l-2 border-primary/50">
              "{evidence_b_quote || fact_b.quote}"
            </blockquote>
          )}
        </div>
      </div>

      {/* Rationale & Contextual Factors */}
      <div className="p-3.5 rounded-lg bg-muted/30 border border-border/60 text-xs space-y-1.5">
        <div className="flex items-center gap-1.5 font-semibold text-foreground/90">
          <ArrowRightLeft className="h-3.5 w-3.5 text-primary" />
          <span>System Reasoning & Rationale</span>
        </div>
        <p className="text-xs text-foreground/80 leading-relaxed font-sans pl-5">
          {rationale}
        </p>

        {contextual_factors && Object.keys(contextual_factors).length > 0 && (
          <div className="flex flex-wrap gap-2 pl-5 pt-1">
            {Object.entries(contextual_factors).map(([k, v]) => (
              <span
                key={k}
                className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono bg-background border border-border/60 text-muted-foreground"
              >
                <b className="text-foreground/80 mr-1">{k}:</b> {String(v)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
