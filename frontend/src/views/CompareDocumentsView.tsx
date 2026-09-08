import { useEffect, useState, useMemo } from "react";
import {
  FileText,
  TrendingUp,
  TrendingDown,
  Minus,
  PlusCircle,
  Layers,
  Search,
  Check,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  X,
} from "lucide-react";
import { api } from "@/api/client";
import {
  DocumentResponse,
  DocumentComparisonResponse,
  MetricComparisonItem,
} from "@/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";

interface CompareDocumentsViewProps {
  datasetId?: string;
  onInspectFact?: (factId: string) => void;
}

export function CompareDocumentsView({
  datasetId,
  onInspectFact,
}: CompareDocumentsViewProps) {
  const [availableDocs, setAvailableDocs] = useState<DocumentResponse[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<DocumentComparisonResponse | null>(null);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [filterCategory, setFilterCategory] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeDrilldown, setActiveDrilldown] = useState<MetricComparisonItem | null>(null);

  // 1. Fetch available documents
  useEffect(() => {
    setLoadingDocs(true);
    api.getDocuments(datasetId)
      .then((docs) => {
        setAvailableDocs(docs);
        // Default to first 2 documents
        if (docs.length >= 2) {
          setSelectedDocIds([docs[0].id, docs[1].id]);
        } else if (docs.length === 1) {
          setSelectedDocIds([docs[0].id]);
        }
      })
      .catch((err) => console.error("Failed to load documents for comparison:", err))
      .finally(() => setLoadingDocs(false));
  }, [datasetId]);

  // 2. Fetch comparison whenever selectedDocIds changes (min 2 docs)
  useEffect(() => {
    if (selectedDocIds.length < 2) {
      setComparison(null);
      return;
    }

    setComparing(true);
    api.compareDocuments(selectedDocIds)
      .then(setComparison)
      .catch((err) => {
        console.error("Comparison failed:", err);
        setComparison(null);
      })
      .finally(() => setComparing(false));
  }, [selectedDocIds]);

  const toggleDocSelection = (docId: string) => {
    if (selectedDocIds.includes(docId)) {
      if (selectedDocIds.length > 2) {
        setSelectedDocIds(selectedDocIds.filter((id) => id !== docId));
      }
    } else {
      if (selectedDocIds.length < 5) {
        setSelectedDocIds([...selectedDocIds, docId]);
      }
    }
  };

  // Client-side filtering
  const filteredMetrics = useMemo(() => {
    if (!comparison) return [];
    return comparison.metrics.filter((item) => {
      // Category filter
      if (filterCategory !== "ALL") {
        if (filterCategory === "CHANGES_ONLY") {
          if (item.category === "UNCHANGED") return false;
        } else if (filterCategory === "ADDED_OR_NOT_FOUND") {
          if (item.category !== "ADDED" && item.category !== "NOT_FOUND") return false;
        } else if (item.category !== filterCategory) {
          return false;
        }
      }

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const mPred = item.predicate.toLowerCase().includes(q);
        const mSubj = item.subject.toLowerCase().includes(q);
        const mRawA = item.doc_a_value?.raw_value.toLowerCase().includes(q);
        const mRawB = item.doc_b_value?.raw_value.toLowerCase().includes(q);
        return mPred || mSubj || mRawA || mRawB;
      }

      return true;
    });
  }, [comparison, filterCategory, searchQuery]);

  return (
    <div className="space-y-5 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-1">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-foreground">
              What Changed? — Cross-Document Comparison
            </h2>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-primary/10 text-primary font-semibold border border-primary/20">
              Analytical Variance
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-1 max-w-3xl leading-relaxed">
            Multi-document financial trend analysis. Automatically identifies increased, decreased, unchanged, and scope-divergent metrics across filings with zero extra LLM calls.
          </p>
        </div>
      </div>

      {/* Document Selector Pills (2 to 5 documents) */}
      <div className="p-4 rounded-xl border border-border bg-card/80 space-y-2.5 shadow-sm">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="font-semibold text-foreground flex items-center gap-1.5">
            <FileText className="h-3.5 w-3.5 text-primary" />
            Select Documents to Compare (2 to 5 filings)
          </span>
          <span className="text-[11px] font-mono">
            {selectedDocIds.length} of {Math.min(5, availableDocs.length)} selected
          </span>
        </div>

        {loadingDocs ? (
          <div className="flex gap-2">
            <Skeleton className="h-8 w-48 rounded-lg" />
            <Skeleton className="h-8 w-48 rounded-lg" />
          </div>
        ) : availableDocs.length < 2 ? (
          <div className="text-xs text-muted-foreground italic py-2">
            At least two documents must be ingested in this dataset to compare changes.
          </div>
        ) : (
          <div className="flex flex-wrap gap-2 pt-1">
            {availableDocs.map((doc) => {
              const isSelected = selectedDocIds.includes(doc.id);
              return (
                <button
                  key={doc.id}
                  onClick={() => toggleDocSelection(doc.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 ${
                    isSelected
                      ? "bg-primary/15 text-primary border-primary/40 font-semibold shadow-sm ring-1 ring-primary/20"
                      : "bg-muted/40 text-muted-foreground border-border hover:text-foreground hover:bg-muted"
                  }`}
                >
                  <div
                    className={`h-3 w-3 rounded-full flex items-center justify-center text-[9px] ${
                      isSelected ? "bg-primary text-primary-foreground font-bold" : "border border-muted-foreground"
                    }`}
                  >
                    {isSelected && <Check className="h-2.5 w-2.5 stroke-[3]" />}
                  </div>
                  <span className="truncate max-w-[280px]">{doc.filename}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Summary Stats Cards */}
      {comparison && (
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-2.5">
          <div className="p-3 rounded-xl border border-border bg-card/60 space-y-1">
            <div className="text-[11px] text-muted-foreground">Total Metrics</div>
            <div className="text-xl font-bold font-mono text-foreground">
              {comparison.summary.total_metrics_compared}
            </div>
          </div>

          <div className="p-3 rounded-xl border border-emerald-500/30 bg-emerald-500/[0.03] space-y-1">
            <div className="text-[11px] text-emerald-400 flex items-center gap-1">
              <TrendingUp className="h-3 w-3" /> Increased
            </div>
            <div className="text-xl font-bold font-mono text-emerald-400">
              {comparison.summary.increased_count}
            </div>
          </div>

          <div className="p-3 rounded-xl border border-rose-500/30 bg-rose-500/[0.03] space-y-1">
            <div className="text-[11px] text-rose-400 flex items-center gap-1">
              <TrendingDown className="h-3 w-3" /> Decreased
            </div>
            <div className="text-xl font-bold font-mono text-rose-400">
              {comparison.summary.decreased_count}
            </div>
          </div>

          <div className="p-3 rounded-xl border border-border/80 bg-card/60 space-y-1">
            <div className="text-[11px] text-muted-foreground flex items-center gap-1">
              <Minus className="h-3 w-3" /> Unchanged
            </div>
            <div className="text-xl font-bold font-mono text-muted-foreground">
              {comparison.summary.unchanged_count}
            </div>
          </div>

          <div className="p-3 rounded-xl border border-amber-500/30 bg-amber-500/[0.03] space-y-1">
            <div className="text-[11px] text-amber-400 flex items-center gap-1">
              <Layers className="h-3 w-3" /> Scope / Context
            </div>
            <div className="text-xl font-bold font-mono text-amber-400">
              {comparison.summary.context_changed_count}
            </div>
          </div>

          <div className="p-3 rounded-xl border border-sky-500/30 bg-sky-500/[0.03] space-y-1">
            <div className="text-[11px] text-sky-400 flex items-center gap-1">
              <PlusCircle className="h-3 w-3" /> Distinct Filing
            </div>
            <div className="text-xl font-bold font-mono text-sky-400">
              {comparison.summary.added_count + comparison.summary.not_found_count}
            </div>
          </div>
        </div>
      )}

      {/* Filter Bar & Search */}
      {comparison && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-xl border border-border bg-card/60">
          <div className="flex flex-wrap gap-1.5 text-xs">
            <FilterPill
              label="All Metrics"
              count={comparison.summary.total_metrics_compared}
              active={filterCategory === "ALL"}
              onClick={() => setFilterCategory("ALL")}
            />
            <FilterPill
              label="Increased"
              count={comparison.summary.increased_count}
              active={filterCategory === "INCREASED"}
              onClick={() => setFilterCategory("INCREASED")}
              color="text-emerald-400"
            />
            <FilterPill
              label="Decreased"
              count={comparison.summary.decreased_count}
              active={filterCategory === "DECREASED"}
              onClick={() => setFilterCategory("DECREASED")}
              color="text-rose-400"
            />
            <FilterPill
              label="Unchanged"
              count={comparison.summary.unchanged_count}
              active={filterCategory === "UNCHANGED"}
              onClick={() => setFilterCategory("UNCHANGED")}
            />
            <FilterPill
              label="Scope / Context Changed"
              count={comparison.summary.context_changed_count}
              active={filterCategory === "CONTEXT_CHANGED"}
              onClick={() => setFilterCategory("CONTEXT_CHANGED")}
              color="text-amber-400"
            />
          </div>

          <div className="relative sm:w-64">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Filter by metric (e.g. EBITDA)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 pl-8 text-xs bg-background"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Comparisons Table */}
      {comparing ? (
        <div className="p-12 text-center text-xs text-muted-foreground space-y-3">
          <RefreshCw className="h-6 w-6 animate-spin mx-auto text-primary" />
          <p>Analyzing changes across filings...</p>
        </div>
      ) : !comparison || comparison.metrics.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No Comparative Facts Found"
          description="Select at least two documents with extracted facts to compare numerical and contextual changes."
        />
      ) : (
        <div className="border border-border rounded-xl overflow-hidden bg-card shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-muted/40 border-b border-border text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Metric & Subject</th>
                  {comparison.documents.length === 2 ? (
                    <>
                      <th className="py-3 px-4 truncate max-w-[220px]">
                        {comparison.documents[0].filename}
                      </th>
                      <th className="py-3 px-4 truncate max-w-[220px]">
                        {comparison.documents[1].filename}
                      </th>
                      <th className="py-3 px-4">Calculated Change</th>
                    </>
                  ) : (
                    comparison.documents.map((d) => (
                      <th key={d.id} className="py-3 px-3 truncate max-w-[160px]">
                        {d.filename}
                      </th>
                    ))
                  )}
                  <th className="py-3 px-4 text-right">Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {filteredMetrics.map((item) => {
                  const is2Doc = comparison.documents.length === 2;
                  return (
                    <tr
                      key={item.metric_id}
                      onClick={() => setActiveDrilldown(item)}
                      className="hover:bg-muted/30 transition-colors cursor-pointer group"
                    >
                      {/* Metric Name */}
                      <td className="py-3 px-4">
                        <div className="font-semibold text-foreground flex items-center gap-1.5">
                          <span>{item.predicate}</span>
                        </div>
                        <div className="text-[10px] text-muted-foreground flex items-center gap-1.5 mt-0.5">
                          <span>{item.subject}</span>
                          {item.unit && <span>• {item.unit}</span>}
                          {item.scope && (
                            <span className="px-1.5 py-0.2 rounded bg-muted text-muted-foreground text-[9px]">
                              {item.scope}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* 2-Document Mode */}
                      {is2Doc ? (
                        <>
                          <td className="py-3 px-4">
                            {item.doc_a_value ? (
                              <div className="space-y-0.5">
                                <div className="font-mono font-medium text-foreground">
                                  {item.doc_a_value.raw_value}
                                </div>
                                <div className="text-[10px] text-muted-foreground">
                                  p. {item.doc_a_value.page_number ?? "?"} • {item.doc_a_value.period || "N/A"}
                                </div>
                              </div>
                            ) : (
                              <span className="text-muted-foreground/60 italic text-[11px]">
                                Not in Document A
                              </span>
                            )}
                          </td>

                          <td className="py-3 px-4">
                            {item.doc_b_value ? (
                              <div className="space-y-0.5">
                                <div className="font-mono font-medium text-foreground">
                                  {item.doc_b_value.raw_value}
                                </div>
                                <div className="text-[10px] text-muted-foreground">
                                  p. {item.doc_b_value.page_number ?? "?"} • {item.doc_b_value.period || "N/A"}
                                </div>
                              </div>
                            ) : (
                              <span className="text-muted-foreground/60 italic text-[11px]">
                                Not found in Doc B
                              </span>
                            )}
                          </td>

                          <td className="py-3 px-4">
                            <ChangeBadge item={item} />
                          </td>
                        </>
                      ) : (
                        /* Multi-Document Timeline Mode (3-5 Docs) */
                        comparison.documents.map((d, idx) => {
                          const pt = item.timeline[idx];
                          return (
                            <td key={d.id} className="py-3 px-3">
                              {pt ? (
                                <div className="space-y-0.5">
                                  <div className="font-mono font-medium text-foreground text-[11px]">
                                    {pt.raw_value}
                                  </div>
                                  <div className="text-[9px] text-muted-foreground">
                                    p. {pt.page_number ?? "?"}
                                  </div>
                                </div>
                              ) : (
                                <span className="text-muted-foreground/40 italic text-[10px]">—</span>
                              )}
                            </td>
                          );
                        })
                      )}

                      {/* Evidence Drilldown Action */}
                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 text-xs text-primary group-hover:bg-primary/10"
                        >
                          Evidence <ChevronRight className="h-3 w-3 ml-1" />
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Side-by-Side Evidence Drilldown Modal / Drawer */}
      {activeDrilldown && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-background/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
            <div className="w-screen max-w-2xl bg-card border-l border-border shadow-2xl flex flex-col">
              <div className="p-5 border-b border-border flex items-start justify-between bg-muted/20">
                <div>
                  <div className="text-[10px] font-mono text-primary uppercase font-bold tracking-wider">
                    Source Evidence Drilldown
                  </div>
                  <h3 className="text-base font-bold text-foreground">
                    {activeDrilldown.predicate}
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    {activeDrilldown.subject} • {activeDrilldown.change_label}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setActiveDrilldown(null)}
                  className="h-8 w-8 rounded-full"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-5">
                <div className="p-3.5 rounded-xl border border-border bg-muted/30 flex items-center justify-between">
                  <span className="text-xs font-semibold text-foreground">Calculated Change</span>
                  <ChangeBadge item={activeDrilldown} />
                </div>

                {/* Evidence per Document */}
                <div className="space-y-4">
                  {activeDrilldown.timeline.map((point, idx) => {
                    if (!point) return null;
                    return (
                      <div
                        key={idx}
                        className="p-4 rounded-xl border border-border/80 bg-muted/20 space-y-2.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-xs text-foreground truncate max-w-[340px]">
                            {point.document_filename}
                          </span>
                          <span className="text-[11px] font-mono font-bold text-primary">
                            PDF Page {point.page_number ?? "?"}
                          </span>
                        </div>

                        <div className="flex items-baseline gap-2">
                          <span className="text-lg font-bold font-mono text-foreground">
                            {point.raw_value}
                          </span>
                          {point.period && (
                            <span className="text-[10px] text-muted-foreground">
                              ({point.period})
                            </span>
                          )}
                          {point.scope && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-muted text-muted-foreground">
                              {point.scope}
                            </span>
                          )}
                        </div>

                        {point.evidence_quote && (
                          <blockquote className="text-xs italic text-muted-foreground border-l-2 border-primary/50 pl-3 leading-relaxed">
                            "{point.evidence_quote}"
                          </blockquote>
                        )}

                        {onInspectFact && point.fact_id && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              onInspectFact(point.fact_id);
                              setActiveDrilldown(null);
                            }}
                            className="h-6 px-2 text-[10px] text-primary"
                          >
                            <ExternalLink className="h-3 w-3 mr-1" />
                            Open in Fact Explorer
                          </Button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function FilterPill({
  label,
  count,
  active,
  onClick,
  color,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
  color?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-2.5 py-1 rounded-md text-xs font-medium border transition-all flex items-center gap-1.5 ${
        active
          ? "bg-primary text-primary-foreground font-semibold border-primary shadow-sm"
          : "bg-muted/40 text-muted-foreground border-border/70 hover:text-foreground hover:bg-muted"
      }`}
    >
      <span className={active ? "" : color}>{label}</span>
      <span
        className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
          active ? "bg-primary-foreground/20 text-primary-foreground" : "bg-muted text-muted-foreground"
        }`}
      >
        {count}
      </span>
    </button>
  );
}

function ChangeBadge({ item }: { item: MetricComparisonItem }) {
  if (item.category === "INCREASED") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
        <TrendingUp className="h-3 w-3" /> {item.change_label}
      </span>
    );
  }
  if (item.category === "DECREASED") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
        <TrendingDown className="h-3 w-3" /> {item.change_label}
      </span>
    );
  }
  if (item.category === "CONTEXT_CHANGED") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-amber-500/15 text-amber-400 border border-amber-500/30">
        <Layers className="h-3 w-3" /> {item.change_label}
      </span>
    );
  }
  if (item.category === "ADDED") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-sky-500/15 text-sky-400 border border-sky-500/30">
        <PlusCircle className="h-3 w-3" /> Added
      </span>
    );
  }
  if (item.category === "NOT_FOUND") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono text-muted-foreground bg-muted/60 border border-border">
        {item.change_label}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono text-muted-foreground bg-muted/60 border border-border">
      <Minus className="h-3 w-3" /> No change
    </span>
  );
}
