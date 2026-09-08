import { useEffect, useState } from "react";
import {
  X,
  AlertTriangle,
  CheckCircle2,
  Scale,
  FileText,
  Layers,
  ShieldCheck,
  ExternalLink,
  Loader2,
} from "lucide-react";
import { api } from "@/api/client";
import { InvestigationResponse, RelationshipWithDetailsResponse } from "@/api/types";
import { Button } from "@/components/ui/button";

interface InvestigationDrawerProps {
  relationship: RelationshipWithDetailsResponse | null;
  isOpen: boolean;
  onClose: () => void;
  onInspectFact?: (factId: string) => void;
}

export function InvestigationDrawer({
  relationship,
  isOpen,
  onClose,
  onInspectFact,
}: InvestigationDrawerProps) {
  const [data, setData] = useState<InvestigationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !relationship) {
      setData(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    api.getRelationshipInvestigation(relationship.id)
      .then((res) => setData(res))
      .catch((err) => {
        console.error("Failed to fetch investigation:", err);
        setError("Failed to run contradiction investigation.");
      })
      .finally(() => setLoading(false));
  }, [isOpen, relationship]);

  if (!isOpen || !relationship) return null;

  const checks = data?.checks;
  const isContradiction = data?.verdict_type === "TRUE_CONTRADICTION";
  const isContextual = data?.verdict_type === "CONTEXTUAL_DIFFERENCE";
  const isCorroborated = data?.verdict_type === "CORROBORATED" || data?.verdict_type === "UNIT_DIFFERENCE";
  const isTemporal = data?.verdict_type === "TEMPORAL_DIFFERENCE";

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-2xl bg-card border-l border-border shadow-2xl flex flex-col">
          {/* Header */}
          <div className="p-5 border-b border-border flex items-start justify-between bg-muted/20">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="p-1.5 rounded-lg bg-primary/10 text-primary">
                  <Scale className="h-4 w-4" />
                </span>
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-primary">
                  Contradiction Investigator
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-muted font-medium border border-border">
                  Deterministic Audit
                </span>
              </div>
              <h3 className="text-base font-bold text-foreground tracking-tight">
                {data?.metric_name || relationship.fact_a.predicate}
              </h3>
              <p className="text-xs text-muted-foreground">
                Exhaustive multi-factor reconciliation between source filings.
              </p>
            </div>

            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="h-8 w-8 rounded-full hover:bg-muted"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {loading && (
              <div className="flex flex-col items-center justify-center py-20 text-muted-foreground space-y-3">
                <Loader2 className="h-7 w-7 animate-spin text-primary" />
                <p className="text-xs font-medium">Running multi-factor discrepancy audit...</p>
              </div>
            )}

            {error && (
              <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-400 text-xs">
                {error}
              </div>
            )}

            {data && !loading && (
              <>
                {/* Variance Comparison Box */}
                <div className="p-4 rounded-xl border border-border bg-muted/30 space-y-3">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="font-semibold text-foreground">Observed Figures</span>
                    {typeof data.variance_percent === "number" && (
                      <span
                        className={`font-mono font-bold px-2 py-0.5 rounded text-xs ${
                          Math.abs(data.variance_percent) <= 1.5
                            ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                            : isContextual
                            ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                            : isContradiction
                            ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                            : "bg-muted text-muted-foreground border border-border"
                        }`}
                      >
                        Variance: {data.variance_percent > 0 ? `+${data.variance_percent}%` : `${data.variance_percent}%`}
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg bg-card border border-border/80 space-y-1">
                      <div className="text-[10px] text-muted-foreground truncate font-mono">
                        {data.source_a.document || "Document A"} (p. {data.source_a.page ?? "?"})
                      </div>
                      <div className="text-base font-bold text-foreground font-mono">
                        {data.value_a_display}
                      </div>
                      <div className="text-[10px] text-muted-foreground">
                        {data.source_a.scope || "Unspecified Scope"} • {data.source_a.period || "Unspecified Period"}
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-card border border-border/80 space-y-1">
                      <div className="text-[10px] text-muted-foreground truncate font-mono">
                        {data.source_b.document || "Document B"} (p. {data.source_b.page ?? "?"})
                      </div>
                      <div className="text-base font-bold text-foreground font-mono">
                        {data.value_b_display}
                      </div>
                      <div className="text-[10px] text-muted-foreground">
                        {data.source_b.scope || "Unspecified Scope"} • {data.source_b.period || "Unspecified Period"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Deterministic Investigation Checklist */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                    Investigation Checklist
                  </h4>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <CheckItem label="Entity Match" pass={checks?.entity_match} />
                    <CheckItem label="Metric Match" pass={checks?.predicate_match} />
                    <CheckItem label="Period Match" pass={checks?.period_match} />
                    <CheckItem label="Currency Match" pass={checks?.currency_match} />
                    <CheckItem label="Unit Match" pass={checks?.unit_match} />
                    <CheckItem
                      label="Scope Match"
                      pass={checks?.scope_match}
                      note={!checks?.scope_match ? "Consolidated vs Standalone" : undefined}
                    />
                  </div>
                </div>

                {/* Verdict Card */}
                <div
                  className={`p-4 rounded-xl border space-y-2 ${
                    isCorroborated
                      ? "bg-emerald-500/[0.05] border-emerald-500/30"
                      : isContextual || isTemporal
                      ? "bg-amber-500/[0.05] border-amber-500/30"
                      : "bg-rose-500/[0.05] border-rose-500/30"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {isCorroborated ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                      ) : isContextual || isTemporal ? (
                        <Layers className="h-4 w-4 text-amber-500" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 text-rose-500" />
                      )}
                      <span className="font-bold text-xs uppercase tracking-tight text-foreground">
                        Verdict: {data.verdict}
                      </span>
                    </div>

                    <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-muted/60 text-muted-foreground">
                      Investigation Confidence: {data.confidence}%
                    </span>
                  </div>

                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {data.explanation}
                  </p>

                  <div className="pt-1 flex items-center justify-between text-[11px]">
                    <span className="text-muted-foreground">
                      Status:{" "}
                      <b className={data.review_required ? "text-rose-400" : "text-emerald-400"}>
                        {data.review_required ? "Audit Review Recommended" : "Reconciled via Context"}
                      </b>
                    </span>
                  </div>
                </div>

                {/* Source Quotes Evidence Comparison */}
                <div className="space-y-3 pt-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <FileText className="h-3.5 w-3.5 text-primary" />
                    Source Grounding Evidence
                  </h4>

                  <div className="space-y-2.5">
                    {/* Source A */}
                    <div className="p-3.5 rounded-xl border border-border/80 bg-muted/20 space-y-2">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-semibold text-foreground truncate max-w-[320px]">
                          {data.source_a.document}
                        </span>
                        <span className="text-[10px] font-mono text-muted-foreground">
                          Page {data.source_a.page ?? "?"}
                        </span>
                      </div>
                      <blockquote className="text-xs italic text-muted-foreground border-l-2 border-primary/40 pl-3 leading-relaxed">
                        "{data.source_a.quote || data.source_a.raw_claim}"
                      </blockquote>
                      {onInspectFact && data.source_a.fact_id && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onInspectFact(data.source_a.fact_id)}
                          className="h-6 px-2 text-[10px] text-primary"
                        >
                          <ExternalLink className="h-3 w-3 mr-1" />
                          Inspect Fact A Details
                        </Button>
                      )}
                    </div>

                    {/* Source B */}
                    <div className="p-3.5 rounded-xl border border-border/80 bg-muted/20 space-y-2">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-semibold text-foreground truncate max-w-[320px]">
                          {data.source_b.document}
                        </span>
                        <span className="text-[10px] font-mono text-muted-foreground">
                          Page {data.source_b.page ?? "?"}
                        </span>
                      </div>
                      <blockquote className="text-xs italic text-muted-foreground border-l-2 border-primary/40 pl-3 leading-relaxed">
                        "{data.source_b.quote || data.source_b.raw_claim}"
                      </blockquote>
                      {onInspectFact && data.source_b.fact_id && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onInspectFact(data.source_b.fact_id)}
                          className="h-6 px-2 text-[10px] text-primary"
                        >
                          <ExternalLink className="h-3 w-3 mr-1" />
                          Inspect Fact B Details
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function CheckItem({ label, pass, note }: { label: string; pass?: boolean; note?: string }) {
  return (
    <div className="p-2 rounded-lg border border-border/60 bg-card/50 flex items-center justify-between">
      <div className="flex items-center gap-2">
        {pass ? (
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
        ) : (
          <X className="h-3.5 w-3.5 text-rose-500 shrink-0" />
        )}
        <span className="font-medium">{label}</span>
      </div>
      <span className={`text-[10px] font-mono ${pass ? "text-emerald-500" : "text-rose-400"}`}>
        {pass ? "MATCH" : note ? note : "DIFF"}
      </span>
    </div>
  );
}
