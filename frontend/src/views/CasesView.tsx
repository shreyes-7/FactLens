import { useEffect, useState } from "react";
import {
  Award,
  CheckCircle2,
  AlertTriangle,
  Layers,
  HelpCircle,
  FileText,
  ArrowRightLeft,
  ShieldCheck,
  Quote,
} from "lucide-react";
import { api } from "@/api/client";
import { FourCasesResponse } from "@/api/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatNormalizedValue } from "@/lib/formatters";

export function CasesView() {
  const [data, setData] = useState<FourCasesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeCaseNumber, setActiveCaseNumber] = useState<number>(1);

  useEffect(() => {
    setLoading(true);
    api.getFourCases()
      .then(setData)
      .catch((err) => console.error("Failed to load 4 cases:", err))
      .finally(() => setLoading(false));
  }, []);

  const activeCase = data?.cases.find((c) => c.case_number === activeCaseNumber) || data?.cases[0];

  const getCaseIcon = (type: string) => {
    switch (type) {
      case "CORROBORATES":
        return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
      case "CONTRADICTS":
        return <AlertTriangle className="h-4 w-4 text-rose-500" />;
      case "CONTEXTUAL_DIFFERENCE":
        return <Layers className="h-4 w-4 text-amber-500" />;
      case "UNCERTAIN":
      default:
        return <HelpCircle className="h-4 w-4 text-zinc-400" />;
    }
  };

  const getCaseBadgeClass = (type: string) => {
    switch (type) {
      case "CORROBORATES":
        return "bg-emerald-500/10 text-emerald-500 border-emerald-500/30";
      case "CONTRADICTS":
        return "bg-rose-500/10 text-rose-500 border-rose-500/30";
      case "CONTEXTUAL_DIFFERENCE":
        return "bg-amber-500/10 text-amber-500 border-amber-500/30";
      case "UNCERTAIN":
      default:
        return "bg-zinc-500/10 text-zinc-400 border-zinc-500/30";
    }
  };

  return (
    <div className="space-y-5 animate-in fade-in duration-150">
      {/* Header Banner */}
      <div className="p-5 rounded-xl border border-border/80 bg-card/60 space-y-1">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-md bg-emerald-500/20 text-emerald-500 flex items-center justify-center">
            <Award className="h-4 w-4" />
          </div>
          <h2 className="text-lg font-bold tracking-tight text-foreground">
            Superjoin Assignment Benchmark Cases
          </h2>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed pl-9">
          This dedicated showcase directly demonstrates the 4 required evaluation cases from the hiring specification using real extracted facts, exact PDF page quotes, and automated reconciliation rationales.
        </p>
      </div>

      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : data ? (
        <div className="space-y-4">
          {/* Case Navigation Tabs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
            {data.cases.map((c) => {
              const isSelected = activeCase?.case_number === c.case_number;
              return (
                <button
                  key={c.case_number}
                  onClick={() => setActiveCaseNumber(c.case_number)}
                  className={`p-3.5 rounded-xl border text-left transition-all relative overflow-hidden ${
                    isSelected
                      ? "border-primary bg-primary/10 shadow-sm ring-1 ring-primary/30"
                      : "border-border/70 bg-card/50 hover:bg-muted/40 hover:border-border"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground">
                      Case 0{c.case_number}
                    </span>
                    {getCaseIcon(c.case_type)}
                  </div>
                  <h4 className="mt-1.5 text-xs font-bold text-foreground line-clamp-1">
                    {c.case_title}
                  </h4>
                  <p className="mt-0.5 text-[10px] text-muted-foreground line-clamp-1 font-mono">
                    Type: {c.case_type}
                  </p>
                </button>
              );
            })}
          </div>

          {/* Active Case Inspection View */}
          {activeCase && (
            <Card className="border-border/90 bg-card overflow-hidden shadow-sm">
              <CardHeader className="p-5 border-b border-border/60 bg-muted/20">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-foreground text-background">
                        Case #{activeCase.case_number}
                      </span>
                      <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-md border ${getCaseBadgeClass(activeCase.case_type)}`}>
                        {activeCase.case_type}
                      </span>
                    </div>
                    <CardTitle className="text-base font-bold text-foreground">
                      {activeCase.case_title}
                    </CardTitle>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs font-mono text-emerald-500 bg-emerald-500/10 px-2.5 py-1 rounded-md border border-emerald-500/20">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    <span>Evidence Grounded</span>
                  </div>
                </div>
                <CardDescription className="text-xs text-foreground/80 pt-1 leading-relaxed">
                  {activeCase.description}
                </CardDescription>
              </CardHeader>

              <CardContent className="p-5 space-y-5">
                {/* Side-by-side Evidence & Facts */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Fact A */}
                  <div className="p-4 rounded-xl border border-border/80 bg-muted/15 space-y-3">
                    <div className="flex items-center justify-between border-b border-border/40 pb-2 text-xs">
                      <span className="flex items-center gap-1.5 font-medium text-foreground truncate max-w-[200px]">
                        <FileText className="h-4 w-4 text-primary" />
                        {activeCase.fact_a.document_filename || "Document A"}
                      </span>
                      {activeCase.fact_a.page_number && (
                        <span className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded">
                          Page {activeCase.fact_a.page_number}
                        </span>
                      )}
                    </div>

                    <div>
                      <p className="text-[10px] uppercase font-semibold text-muted-foreground">Predicate / Metric</p>
                      <p className="text-sm font-bold text-foreground mt-0.5">{activeCase.fact_a.predicate}</p>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                      <div className="p-2 rounded bg-background border border-border/40">
                        <span className="text-[10px] text-muted-foreground uppercase font-semibold">Raw Claim</span>
                        <p className="font-bold font-mono text-foreground mt-0.5">{activeCase.fact_a.raw_value}</p>
                      </div>
                      <div className="p-2 rounded bg-background border border-border/40">
                        <span className="text-[10px] text-muted-foreground uppercase font-semibold">Normalized Value</span>
                        <p className="font-bold font-mono text-primary mt-0.5">
                          {formatNormalizedValue(activeCase.fact_a.normalized_value, activeCase.fact_a.unit)}
                        </p>
                      </div>
                    </div>

                    {activeCase.evidence_a && (
                      <div className="pt-2">
                        <span className="text-[10px] uppercase font-semibold text-muted-foreground flex items-center gap-1">
                          <Quote className="h-3 w-3" /> Exact Source Quote:
                        </span>
                        <blockquote className="mt-1 p-2.5 rounded bg-muted/40 font-mono text-xs text-foreground italic border-l-2 border-primary leading-relaxed">
                          "{activeCase.evidence_a}"
                        </blockquote>
                      </div>
                    )}
                  </div>

                  {/* Fact B */}
                  {activeCase.fact_b ? (
                    <div className="p-4 rounded-xl border border-border/80 bg-muted/15 space-y-3">
                      <div className="flex items-center justify-between border-b border-border/40 pb-2 text-xs">
                        <span className="flex items-center gap-1.5 font-medium text-foreground truncate max-w-[200px]">
                          <FileText className="h-4 w-4 text-primary" />
                          {activeCase.fact_b.document_filename || "Document B"}
                        </span>
                        {activeCase.fact_b.page_number && (
                          <span className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded">
                            Page {activeCase.fact_b.page_number}
                          </span>
                        )}
                      </div>

                      <div>
                        <p className="text-[10px] uppercase font-semibold text-muted-foreground">Predicate / Metric</p>
                        <p className="text-sm font-bold text-foreground mt-0.5">{activeCase.fact_b.predicate}</p>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                        <div className="p-2 rounded bg-background border border-border/40">
                          <span className="text-[10px] text-muted-foreground uppercase font-semibold">Raw Claim</span>
                          <p className="font-bold font-mono text-foreground mt-0.5">{activeCase.fact_b.raw_value}</p>
                        </div>
                        <div className="p-2 rounded bg-background border border-border/40">
                          <span className="text-[10px] text-muted-foreground uppercase font-semibold">Normalized Value</span>
                          <p className="font-bold font-mono text-primary mt-0.5">
                            {formatNormalizedValue(activeCase.fact_b.normalized_value, activeCase.fact_b.unit)}
                          </p>
                        </div>
                      </div>

                      {activeCase.evidence_b && (
                        <div className="pt-2">
                          <span className="text-[10px] uppercase font-semibold text-muted-foreground flex items-center gap-1">
                            <Quote className="h-3 w-3" /> Exact Source Quote:
                          </span>
                          <blockquote className="mt-1 p-2.5 rounded bg-muted/40 font-mono text-xs text-foreground italic border-l-2 border-primary leading-relaxed">
                            "{activeCase.evidence_b}"
                          </blockquote>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-4 rounded-xl border border-dashed border-border/80 flex flex-col items-center justify-center text-center text-xs text-muted-foreground">
                      <HelpCircle className="h-6 w-6 mb-2 text-muted-foreground/60" />
                      <p className="font-medium">Single Fact Uncertainty Test</p>
                      <p className="text-[11px] mt-1 max-w-xs">
                        This test demonstrates how unquantified or incomplete claims are intercepted before creating speculative edges.
                      </p>
                    </div>
                  )}
                </div>

                {/* System Reasoning & Math Breakdown */}
                <div className="p-4 rounded-xl bg-muted/30 border border-border space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-xs text-foreground">
                    <ArrowRightLeft className="h-4 w-4 text-primary" />
                    <span>Automated System Reasoning & Mathematical Reconciliation</span>
                  </div>
                  <p className="text-xs text-foreground/90 leading-relaxed pl-6">
                    {activeCase.system_reasoning}
                  </p>

                  {activeCase.contextual_factors && Object.keys(activeCase.contextual_factors).length > 0 && (
                    <div className="flex flex-wrap gap-2 pl-6 pt-1">
                      {Object.entries(activeCase.contextual_factors).map(([k, v]) => (
                        <span
                          key={k}
                          className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono bg-card border border-border text-foreground/80"
                        >
                          <b className="mr-1 text-primary">{k}:</b> {String(v)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      ) : (
        <div className="p-8 text-center text-xs text-muted-foreground">
          Failed to load benchmark cases from backend.
        </div>
      )}
    </div>
  );
}
