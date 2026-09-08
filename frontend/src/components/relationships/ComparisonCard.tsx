import { useState } from "react";
import {
  FileText,
  Sparkles,
  ArrowRightLeft,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Link2,
  HelpCircle,
  Scale,
  Copy,
  Check,
} from "lucide-react";
import { RelationshipWithDetailsResponse } from "@/api/types";
import { RelationshipBadge } from "@/components/shared/StatusBadge";
import { formatNormalizedValue, formatConfidence } from "@/lib/formatters";
import { Button } from "@/components/ui/button";

interface ComparisonCardProps {
  relationship: RelationshipWithDetailsResponse;
  onInspectFact?: (factId: string) => void;
  onInvestigate?: (relationship: RelationshipWithDetailsResponse) => void;
}

export function ComparisonCard({ relationship, onInspectFact, onInvestigate }: ComparisonCardProps) {
  const {
    fact_a,
    fact_b,
    relationship_type,
    confidence,
    rationale,
    contextual_factors,
    evidence_a_quote,
    evidence_b_quote,
  } = relationship;

  const [copiedQuote, setCopiedQuote] = useState<"a" | "b" | null>(null);

  const isCrossDocument =
    fact_a.document_filename &&
    fact_b.document_filename &&
    fact_a.document_filename !== fact_b.document_filename;

  // Calculate variance if both have normalized numbers
  const valA = fact_a.normalized_value;
  const valB = fact_b.normalized_value;
  let varianceText: string | null = null;
  let varianceType: "exact" | "diff" | null = null;

  if (valA !== null && valA !== undefined && valB !== null && valB !== undefined) {
    const diff = Math.abs(valB - valA);
    const maxVal = Math.max(Math.abs(valA), Math.abs(valB));
    if (diff === 0 || (maxVal > 0 && diff / maxVal < 0.005)) {
      varianceText = "Exact match (~0% variance)";
      varianceType = "exact";
    } else if (maxVal > 0) {
      const pct = ((valB - valA) / Math.abs(valA)) * 100;
      varianceText = `${pct > 0 ? "+" : ""}${pct.toFixed(1)}% variance`;
      varianceType = "diff";
    }
  }

  // Filter contextual factors: only show non-empty, non-trivial attributes
  const validContextualFactors = Object.entries(contextual_factors || {}).filter(([_, v]) => {
    if (v === null || v === undefined) return false;
    const s = String(v).trim().toLowerCase();
    return s !== "" && s !== "none" && s !== "null" && s !== "n/a" && s !== "unspecified";
  });

  const handleCopyQuote = (side: "a" | "b", text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedQuote(side);
    setTimeout(() => setCopiedQuote(null), 2000);
  };

  // Card theme styling based on relationship type
  const getCardTheme = () => {
    switch (relationship_type) {
      case "CORROBORATES":
        return {
          border: "border-emerald-500/30 hover:border-emerald-500/50",
          glow: "bg-gradient-to-b from-emerald-500/[0.04] to-transparent",
          bridgeBg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
          symbol: "=",
          icon: CheckCircle2,
        };
      case "CONTRADICTS":
        return {
          border: "border-rose-500/30 hover:border-rose-500/50",
          glow: "bg-gradient-to-b from-rose-500/[0.04] to-transparent",
          bridgeBg: "bg-rose-500/10 text-rose-400 border-rose-500/30",
          symbol: "≠",
          icon: AlertTriangle,
        };
      case "CONTEXTUAL_DIFFERENCE":
        return {
          border: "border-amber-500/30 hover:border-amber-500/50",
          glow: "bg-gradient-to-b from-amber-500/[0.04] to-transparent",
          bridgeBg: "bg-amber-500/10 text-amber-400 border-amber-500/30",
          symbol: "≈",
          icon: Layers,
        };
      case "RELATED":
        return {
          border: "border-sky-500/30 hover:border-sky-500/50",
          glow: "bg-gradient-to-b from-sky-500/[0.04] to-transparent",
          bridgeBg: "bg-sky-500/10 text-sky-400 border-sky-500/30",
          symbol: "↔",
          icon: Link2,
        };
      default:
        return {
          border: "border-border hover:border-muted-foreground/40",
          glow: "bg-card",
          bridgeBg: "bg-muted text-muted-foreground border-border",
          symbol: "?",
          icon: HelpCircle,
        };
    }
  };

  const theme = getCardTheme();

  return (
    <div
      className={`rounded-2xl border ${theme.border} ${theme.glow} p-5 transition-all duration-200 shadow-sm hover:shadow-md space-y-4`}
    >
      {/* Top Meta Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 pb-3 border-b border-border/50">
        <div className="flex items-center gap-2">
          <RelationshipBadge type={relationship_type} />
          {isCrossDocument ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-primary/10 text-primary border border-primary/20">
              <Scale className="h-3 w-3" />
              Cross-Document Reconciliation
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-muted text-muted-foreground border border-border/50">
              Cross-Section Comparison
            </span>
          )}
          <span className="text-[11px] font-mono text-muted-foreground">
            ID: {relationship.id.slice(0, 8)}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {varianceText && (
            <span
              className={`text-[11px] font-mono font-medium px-2 py-0.5 rounded border ${
                varianceType === "exact"
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                  : "bg-amber-500/10 text-amber-400 border-amber-500/30"
              }`}
            >
              {varianceText}
            </span>
          )}
          <div className="flex items-center gap-1 text-[11px] font-mono font-semibold text-foreground/90 bg-muted/60 px-2.5 py-0.5 rounded-full border border-border/60">
            <Sparkles className="h-3 w-3 text-primary" />
            <span>{formatConfidence(confidence)} Confidence</span>
          </div>
          {onInvestigate && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onInvestigate(relationship)}
              className="h-7 px-2.5 text-xs font-semibold text-primary border-primary/30 hover:bg-primary/10 shadow-sm"
              title="Open Contradiction Investigator for deterministic multi-factor breakdown"
            >
              <Scale className="h-3 w-3 mr-1" />
              Investigate
            </Button>
          )}
        </div>
      </div>

      {/* Side-by-Side Visual Comparison Bridge */}
      <div className="grid grid-cols-1 lg:grid-cols-11 gap-3 items-stretch">
        {/* FACT A */}
        <div className="lg:col-span-5 rounded-xl border border-border/70 bg-card/70 p-4 flex flex-col justify-between space-y-3 hover:border-primary/40 transition-colors">
          <div className="space-y-2.5">
            {/* Document & Page Pill */}
            <div className="flex items-center justify-between text-xs pb-2 border-b border-border/40">
              <span
                className="flex items-center gap-1.5 font-semibold text-foreground truncate max-w-[220px]"
                title={fact_a.document_filename || "Document A"}
              >
                <FileText className="h-3.5 w-3.5 text-primary shrink-0" />
                <span className="truncate">{fact_a.document_filename || "Document A"}</span>
              </span>
              {fact_a.page_number && (
                <span className="font-mono text-[10px] font-semibold bg-primary/10 text-primary px-2 py-0.5 rounded-md border border-primary/20">
                  Page {fact_a.page_number}
                </span>
              )}
            </div>

            {/* Metric & Value */}
            <div>
              <div className="flex items-center justify-between gap-1">
                <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground font-mono">
                  {fact_a.entity || "Entity"} • {fact_a.predicate}
                </span>
              </div>
              <div className="mt-1">
                <div className="text-base font-bold font-mono text-foreground leading-tight">
                  {fact_a.raw_value}
                </div>
                {fact_a.normalized_value !== null && fact_a.normalized_value !== undefined && (
                  <div className="text-xs font-mono text-primary/90 mt-0.5 flex items-center gap-1">
                    <span>Normalized:</span>
                    <span className="font-semibold">
                      {formatNormalizedValue(fact_a.normalized_value, fact_a.unit)}
                    </span>
                    {fact_a.unit && <span className="text-muted-foreground">({fact_a.unit})</span>}
                  </div>
                )}
              </div>
            </div>

            {/* Tags (only if present) */}
            {(fact_a.time_period || fact_a.scope || fact_a.status) && (
              <div className="flex flex-wrap gap-1.5 pt-1 text-[10px]">
                {fact_a.time_period && (
                  <span className="px-2 py-0.5 rounded-md bg-muted text-muted-foreground font-medium">
                    📅 {fact_a.time_period}
                  </span>
                )}
                {fact_a.scope && (
                  <span className="px-2 py-0.5 rounded-md bg-muted text-muted-foreground font-medium">
                    🔍 {fact_a.scope}
                  </span>
                )}
                {fact_a.status && (
                  <span className="px-2 py-0.5 rounded-md bg-muted text-muted-foreground font-medium">
                    🏷️ {fact_a.status}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Evidence Quote Block & Actions */}
          <div className="pt-2 border-t border-border/40 space-y-2">
            {(evidence_a_quote || fact_a.quote) && (
              <div className="relative group p-2.5 rounded-lg bg-muted/40 font-mono text-[11px] text-foreground/80 italic border-l-2 border-primary/60 leading-relaxed">
                "{evidence_a_quote || fact_a.quote}"
                <button
                  onClick={() => handleCopyQuote("a", evidence_a_quote || fact_a.quote || "")}
                  title="Copy evidence quote"
                  className="absolute top-1.5 right-1.5 p-1 rounded bg-background/80 text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  {copiedQuote === "a" ? (
                    <Check className="h-3 w-3 text-emerald-400" />
                  ) : (
                    <Copy className="h-3 w-3" />
                  )}
                </button>
              </div>
            )}

            <Button
              variant="ghost"
              size="sm"
              onClick={() => onInspectFact && onInspectFact(fact_a.id)}
              className="w-full h-7 text-[11px] font-medium text-muted-foreground hover:text-primary hover:bg-primary/5 flex items-center justify-center gap-1"
            >
              <ExternalLink className="h-3 w-3" />
              Inspect Source Grounding
            </Button>
          </div>
        </div>

        {/* COMPARISON BRIDGE (Center Column) */}
        <div className="lg:col-span-1 flex lg:flex-col items-center justify-center gap-2 py-2 lg:py-0">
          <div className="hidden lg:block w-px h-6 bg-border/60" />
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center border shadow-sm ${theme.bridgeBg}`}
            title={`${relationship_type}: ${theme.symbol}`}
          >
            <span className="font-mono font-bold text-base">{theme.symbol}</span>
          </div>
          <div className="hidden lg:block w-px h-6 bg-border/60" />
        </div>

        {/* FACT B */}
        <div className="lg:col-span-5 rounded-xl border border-border/70 bg-card/70 p-4 flex flex-col justify-between space-y-3 hover:border-primary/40 transition-colors">
          <div className="space-y-2.5">
            {/* Document & Page Pill */}
            <div className="flex items-center justify-between text-xs pb-2 border-b border-border/40">
              <span
                className="flex items-center gap-1.5 font-semibold text-foreground truncate max-w-[220px]"
                title={fact_b.document_filename || "Document B"}
              >
                <FileText className="h-3.5 w-3.5 text-primary shrink-0" />
                <span className="truncate">{fact_b.document_filename || "Document B"}</span>
              </span>
              {fact_b.page_number && (
                <span className="font-mono text-[10px] font-semibold bg-primary/10 text-primary px-2 py-0.5 rounded-md border border-primary/20">
                  Page {fact_b.page_number}
                </span>
              )}
            </div>

            {/* Metric & Value */}
            <div>
              <div className="flex items-center justify-between gap-1">
                <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground font-mono">
                  {fact_b.entity || "Entity"} • {fact_b.predicate}
                </span>
              </div>
              <div className="mt-1">
                <div className="text-base font-bold font-mono text-foreground leading-tight">
                  {fact_b.raw_value}
                </div>
                {fact_b.normalized_value !== null && fact_b.normalized_value !== undefined && (
                  <div className="text-xs font-mono text-primary/90 mt-0.5 flex items-center gap-1">
                    <span>Normalized:</span>
                    <span className="font-semibold">
                      {formatNormalizedValue(fact_b.normalized_value, fact_b.unit)}
                    </span>
                    {fact_b.unit && <span className="text-muted-foreground">({fact_b.unit})</span>}
                  </div>
                )}
              </div>
            </div>

            {/* Tags (only if present) */}
            {(fact_b.time_period || fact_b.scope || fact_b.status) && (
              <div className="flex flex-wrap gap-1.5 pt-1 text-[10px]">
                {fact_b.time_period && (
                  <span className="px-2 py-0.5 rounded-md bg-muted text-muted-foreground font-medium">
                    📅 {fact_b.time_period}
                  </span>
                )}
                {fact_b.scope && (
                  <span className="px-2 py-0.5 rounded-md bg-muted text-muted-foreground font-medium">
                    🔍 {fact_b.scope}
                  </span>
                )}
                {fact_b.status && (
                  <span className="px-2 py-0.5 rounded-md bg-muted text-muted-foreground font-medium">
                    🏷️ {fact_b.status}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Evidence Quote Block & Actions */}
          <div className="pt-2 border-t border-border/40 space-y-2">
            {(evidence_b_quote || fact_b.quote) && (
              <div className="relative group p-2.5 rounded-lg bg-muted/40 font-mono text-[11px] text-foreground/80 italic border-l-2 border-primary/60 leading-relaxed">
                "{evidence_b_quote || fact_b.quote}"
                <button
                  onClick={() => handleCopyQuote("b", evidence_b_quote || fact_b.quote || "")}
                  title="Copy evidence quote"
                  className="absolute top-1.5 right-1.5 p-1 rounded bg-background/80 text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  {copiedQuote === "b" ? (
                    <Check className="h-3 w-3 text-emerald-400" />
                  ) : (
                    <Copy className="h-3 w-3" />
                  )}
                </button>
              </div>
            )}

            <Button
              variant="ghost"
              size="sm"
              onClick={() => onInspectFact && onInspectFact(fact_b.id)}
              className="w-full h-7 text-[11px] font-medium text-muted-foreground hover:text-primary hover:bg-primary/5 flex items-center justify-center gap-1"
            >
              <ExternalLink className="h-3 w-3" />
              Inspect Source Grounding
            </Button>
          </div>
        </div>
      </div>

      {/* System Reasoning & Contextual Differences */}
      <div className="p-3.5 rounded-xl bg-card/90 border border-border/70 text-xs space-y-2 shadow-inner">
        <div className="flex items-center gap-2 font-semibold text-foreground">
          <ArrowRightLeft className="h-3.5 w-3.5 text-primary" />
          <span>System Reasoning & Evidence Synthesis</span>
        </div>

        <p className="text-xs text-foreground/85 leading-relaxed font-sans pl-5">
          {rationale}
        </p>

        {validContextualFactors.length > 0 && (
          <div className="flex flex-wrap gap-2 pl-5 pt-1 border-t border-border/40">
            {validContextualFactors.map(([k, v]) => (
              <span
                key={k}
                className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-mono bg-muted border border-border text-foreground/80"
              >
                <b className="text-primary mr-1 capitalize">{k.replace(/_/g, " ")}:</b> {String(v)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
