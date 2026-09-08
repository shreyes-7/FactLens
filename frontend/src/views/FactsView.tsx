import { useEffect, useState } from "react";
import { Search, RefreshCw, FileText, ShieldCheck, Calendar, Layers } from "lucide-react";
import { api } from "@/api/client";
import { FactWithEvidenceResponse } from "@/api/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { formatNormalizedValue } from "@/lib/formatters";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { EvidenceInspector } from "@/components/facts/EvidenceInspector";

interface FactsViewProps {
  datasetId?: string;
  initialFactId?: string | null;
  refreshTrigger?: number;
}

export function FactsView({ datasetId, initialFactId, refreshTrigger }: FactsViewProps) {
  const [facts, setFacts] = useState<FactWithEvidenceResponse[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [confidenceFilter, setConfidenceFilter] = useState<string>("ALL");
  const [selectedFact, setSelectedFact] = useState<FactWithEvidenceResponse | null>(null);

  const fetchFacts = () => {
    setLoading(true);
    api.getFacts({
      datasetId,
      category: categoryFilter !== "ALL" ? categoryFilter : undefined,
      search: search.trim() || undefined,
      limit: 150,
    })
      .then((res) => {
        setFacts(res.facts || []);
        setTotalCount(res.total ?? (res.facts ? res.facts.length : 0));
        if (initialFactId) {
          const found = res.facts.find((f) => f.id === initialFactId);
          if (found) setSelectedFact(found);
        }
      })
      .catch((err) => console.error("Failed to load facts:", err))
      .finally(() => setLoading(false));
  };

  const displayedFacts = facts.filter((fact) => {
    if (confidenceFilter === "ALL") return true;
    const score = fact.confidence ?? (fact.confidence_score ? Math.round(fact.confidence_score * 100) : 85);
    if (confidenceFilter === "HIGH") return score >= 90;
    if (confidenceFilter === "MEDIUM") return score >= 70 && score < 90;
    if (confidenceFilter === "LOW") return score < 70;
    return true;
  });

  useEffect(() => {
    fetchFacts();
  }, [datasetId, categoryFilter, refreshTrigger]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchFacts();
  };

  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-border/60">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-foreground flex items-center gap-2">
            Fact Explorer & Evidence Grounding
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
              {totalCount} Verified Facts
            </span>
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Inspect atomic financial & operational facts extracted across documents with character-level PDF citations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchFacts}
            disabled={loading}
            className="h-8 text-xs shadow-sm hover:border-primary/50"
          >
            <RefreshCw className={`h-3 w-3 mr-1.5 ${loading ? "animate-spin text-primary" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl border border-border bg-card/70 shadow-sm">
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 max-w-sm w-full">
          <div className="relative w-full">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="Search facts by predicate, entity, or claim..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 h-8 text-xs bg-background"
            />
          </div>
          <Button type="submit" size="sm" variant="secondary" className="h-8 text-xs shrink-0 font-medium">
            Search
          </Button>
        </form>

        {/* Category & Confidence Filter Pills */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-medium text-muted-foreground mr-1">Category:</span>
            {["ALL", "NUMERICAL", "SEMANTIC"].map((cat) => (
              <button
                key={cat}
                onClick={() => setCategoryFilter(cat)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  categoryFilter === cat
                    ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                    : "bg-muted text-muted-foreground hover:text-foreground hover:bg-muted/80"
                }`}
              >
                {cat === "ALL" ? "All Facts" : cat.charAt(0) + cat.slice(1).toLowerCase()}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1.5 border-l border-border/60 pl-3">
            <span className="text-[11px] font-medium text-muted-foreground mr-1">Confidence:</span>
            {[
              { id: "ALL", label: "All" },
              { id: "HIGH", label: "High (≥90%)", color: "text-emerald-400" },
              { id: "MEDIUM", label: "Medium", color: "text-amber-400" },
              { id: "LOW", label: "Needs Review", color: "text-rose-400" },
            ].map((lvl) => (
              <button
                key={lvl.id}
                onClick={() => setConfidenceFilter(lvl.id)}
                className={`px-2 py-1 rounded-md text-[11px] font-medium transition-all ${
                  confidenceFilter === lvl.id
                    ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                    : "bg-muted/60 text-muted-foreground hover:text-foreground"
                }`}
              >
                <span className={confidenceFilter === lvl.id ? "" : lvl.color}>{lvl.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* High-Density Fact Table with Controlled Column Layout */}
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-4 space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : displayedFacts.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs table-fixed">
              <thead className="bg-muted/50 border-b border-border/70 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4 w-[280px]">Entity & Claim Predicate</th>
                  <th className="py-3 px-4 w-[260px]">Raw Statement / Value</th>
                  <th className="py-3 px-4 w-[140px]">Normalized</th>
                  <th className="py-3 px-4 w-[130px]">Period & Scope</th>
                  <th className="py-3 px-4 w-[160px]">Source PDF</th>
                  <th className="py-3 px-4 w-[110px]">Confidence</th>
                  <th className="py-3 px-4 w-[120px] text-right">Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {displayedFacts.map((fact) => {
                  const isNumerical = fact.category === "NUMERICAL" || !!fact.normalized_value;
                  const confScore = fact.confidence ?? (fact.confidence_score ? Math.round(fact.confidence_score * 100) : 85);
                  return (
                    <tr
                      key={fact.id}
                      onClick={() => setSelectedFact(fact)}
                      className="hover:bg-muted/40 cursor-pointer transition-colors group"
                    >
                      {/* Entity & Predicate */}
                      <td className="py-3 px-4 align-top">
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span
                              className={`text-[9px] font-mono font-medium px-1.5 py-0.2 rounded border uppercase ${
                                isNumerical
                                  ? "bg-sky-500/10 text-sky-400 border-sky-500/20"
                                  : "bg-violet-500/10 text-violet-400 border-violet-500/20"
                              }`}
                            >
                              {isNumerical ? "Numerical" : "Semantic"}
                            </span>
                          </div>
                          <p
                            className="font-semibold text-foreground group-hover:text-primary transition-colors text-xs leading-snug line-clamp-2"
                            title={fact.predicate}
                          >
                            {fact.predicate}
                          </p>
                          <p className="text-[11px] text-muted-foreground font-medium">
                            {fact.entity}
                          </p>
                        </div>
                      </td>

                      {/* Raw Statement / Value */}
                      <td className="py-3 px-4 align-top">
                        <div
                          className="text-xs text-foreground/90 font-mono line-clamp-2 leading-relaxed bg-muted/20 p-1.5 rounded border border-border/30"
                          title={fact.raw_value}
                        >
                          {fact.raw_value}
                        </div>
                      </td>

                      {/* Normalized Value */}
                      <td className="py-3 px-4 align-top font-mono">
                        {fact.normalized_value !== null && fact.normalized_value !== undefined ? (
                          <div className="font-semibold text-primary text-xs flex flex-col">
                            <span>{formatNormalizedValue(fact.normalized_value, fact.unit)}</span>
                            {fact.unit && (
                              <span className="text-[10px] text-muted-foreground font-normal">
                                {fact.unit}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-muted-foreground font-mono text-[11px]">—</span>
                        )}
                      </td>

                      {/* Period & Scope */}
                      <td className="py-3 px-4 align-top text-muted-foreground">
                        <div className="space-y-0.5">
                          {fact.time_period ? (
                            <div className="flex items-center gap-1 text-[11px] font-mono text-foreground/80">
                              <Calendar className="h-3 w-3 text-muted-foreground shrink-0" />
                              <span className="truncate" title={fact.time_period}>
                                {fact.time_period}
                              </span>
                            </div>
                          ) : (
                            <span className="text-[11px] font-mono">—</span>
                          )}
                          {fact.scope && (
                            <div className="flex items-center gap-1 text-[10px] text-muted-foreground truncate">
                              <Layers className="h-2.5 w-2.5 shrink-0" />
                              <span className="truncate" title={fact.scope}>
                                {fact.scope}
                              </span>
                            </div>
                          )}
                        </div>
                      </td>

                      {/* Source PDF */}
                      <td className="py-3 px-4 align-top text-muted-foreground">
                        <div className="space-y-1">
                          <div
                            className="flex items-center gap-1.5 text-xs text-foreground/80 truncate font-medium"
                            title={fact.document_filename || "Document"}
                          >
                            <FileText className="h-3.5 w-3.5 text-primary shrink-0" />
                            <span className="truncate">{fact.document_filename || "Document"}</span>
                          </div>
                          {fact.page_number && (
                            <span className="inline-block text-[10px] font-mono bg-muted px-1.5 py-0.2 rounded border border-border/40 text-muted-foreground">
                              Page {fact.page_number}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Confidence Score */}
                      <td className="py-3 px-4 align-top">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`h-2 w-2 rounded-full shrink-0 ${
                              confScore >= 90
                                ? "bg-emerald-500"
                                : confScore >= 70
                                ? "bg-amber-500"
                                : "bg-rose-500"
                            }`}
                          />
                          <div className="flex flex-col">
                            <span className="font-mono text-xs font-bold text-foreground">
                              {confScore}%
                            </span>
                            <span
                              className={`text-[9px] font-semibold uppercase ${
                                confScore >= 90
                                  ? "text-emerald-500"
                                  : confScore >= 70
                                  ? "text-amber-500"
                                  : "text-rose-400"
                              }`}
                            >
                              {confScore >= 90 ? "High" : confScore >= 70 ? "Medium" : "Review"}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Evidence Action */}
                      <td className="py-3 px-4 align-top text-right" onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedFact(fact)}
                          className="h-7 px-2 text-xs font-medium border-primary/30 text-primary hover:bg-primary/10 shadow-sm"
                          title="Inspect character-level grounded PDF quotation"
                        >
                          <ShieldCheck className="h-3 w-3 mr-1 text-primary" />
                          Inspect
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No Facts Found"
            description="No extracted facts matched your query. Process additional document pages or adjust your search keywords."
          />
        )}
      </div>

      {/* Signature Evidence Grounding Inspector Drawer */}
      <EvidenceInspector
        fact={selectedFact}
        onClose={() => setSelectedFact(null)}
      />
    </div>
  );
}
