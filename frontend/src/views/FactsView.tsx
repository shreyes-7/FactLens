import { useEffect, useState } from "react";
import { Search, RefreshCw, FileText } from "lucide-react";
import { api } from "@/api/client";
import { FactWithEvidenceResponse } from "@/api/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { formatConfidence, formatNormalizedValue } from "@/lib/formatters";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { EvidenceInspector } from "@/components/facts/EvidenceInspector";

interface FactsViewProps {
  datasetId?: string;
  initialFactId?: string | null;
}

export function FactsView({ datasetId, initialFactId }: FactsViewProps) {
  const [facts, setFacts] = useState<FactWithEvidenceResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [selectedFact, setSelectedFact] = useState<FactWithEvidenceResponse | null>(null);

  const fetchFacts = () => {
    setLoading(true);
    api.getFacts({
      datasetId,
      category: categoryFilter !== "ALL" ? categoryFilter : undefined,
      search: search.trim() || undefined,
      limit: 100,
    })
      .then((res) => {
        setFacts(res.facts || []);
        if (initialFactId) {
          const found = res.facts.find((f) => f.id === initialFactId);
          if (found) setSelectedFact(found);
        }
      })
      .catch((err) => console.error("Failed to load facts:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchFacts();
  }, [datasetId, categoryFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchFacts();
  };

  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-foreground">Fact Explorer & Evidence Grounding</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Explore atomic claims extracted across documents with character-level PDF citations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchFacts} className="h-8 text-xs">
            <RefreshCw className="h-3 w-3 mr-1" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl border border-border bg-card/60">
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
          <Button type="submit" size="sm" variant="secondary" className="h-8 text-xs shrink-0">
            Search
          </Button>
        </form>

        {/* Category Pills */}
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-medium text-muted-foreground mr-1">Category:</span>
          {["ALL", "NUMERICAL", "SEMANTIC"].map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                categoryFilter === cat
                  ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              }`}
            >
              {cat === "ALL" ? "All Facts" : cat.charAt(0) + cat.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      {/* High-Density Fact Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-4 space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : facts.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/40 border-b border-border/60 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Entity & Predicate</th>
                  <th className="py-3 px-4">Raw Value</th>
                  <th className="py-3 px-4">Normalized Value</th>
                  <th className="py-3 px-4">Period</th>
                  <th className="py-3 px-4">Scope</th>
                  <th className="py-3 px-4">Source PDF</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4">Grounding Quote</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {facts.map((fact) => (
                  <tr
                    key={fact.id}
                    onClick={() => setSelectedFact(fact)}
                    className="hover:bg-muted/40 cursor-pointer transition-colors group"
                  >
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-semibold text-foreground group-hover:text-primary transition-colors text-xs">
                          {fact.predicate}
                        </p>
                        <p className="text-[11px] text-muted-foreground mt-0.5">
                          {fact.entity}
                        </p>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-foreground whitespace-nowrap">
                      {fact.raw_value}
                    </td>
                    <td className="py-3 px-4 font-mono text-primary font-medium whitespace-nowrap">
                      {formatNormalizedValue(fact.normalized_value, fact.unit)}
                    </td>
                    <td className="py-3 px-4 text-muted-foreground whitespace-nowrap font-mono text-[11px]">
                      {fact.time_period || "—"}
                    </td>
                    <td className="py-3 px-4 text-muted-foreground whitespace-nowrap">
                      {fact.scope || "—"}
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">
                      <div className="flex items-center gap-1.5 truncate max-w-[160px]" title={fact.document_filename || ""}>
                        <FileText className="h-3.5 w-3.5 text-primary/70 shrink-0" />
                        <span className="truncate">{fact.document_filename || "Document"}</span>
                        {fact.page_number && (
                          <span className="font-mono text-[10px] bg-muted px-1.5 py-0.2 rounded shrink-0">
                            p.{fact.page_number}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap font-mono text-[11px] text-emerald-500">
                      {formatConfidence(fact.confidence_score)}
                    </td>
                    <td className="py-3 px-4 text-muted-foreground max-w-xs truncate italic font-mono text-[11px]">
                      "{fact.quote || (fact.evidence && fact.evidence[0]?.quote) || "—"}"
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No Facts Found"
            description="No extracted facts matched your filters. Process more document pages or adjust your search term."
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
