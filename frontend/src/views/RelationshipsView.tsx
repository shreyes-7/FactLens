import { useEffect, useState, useMemo } from "react";
import {
  Play,
  Sparkles,
  RefreshCw,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Link2,
  Search,
  Scale,
  FileCheck2,
  X,
} from "lucide-react";
import { api } from "@/api/client";
import { RelationshipWithDetailsResponse, RelationshipType } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ComparisonCard } from "@/components/relationships/ComparisonCard";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";

interface RelationshipsViewProps {
  datasetId?: string;
  onInspectFact?: (factId: string) => void;
  refreshTrigger?: number;
}

export function RelationshipsView({ datasetId, onInspectFact, refreshTrigger }: RelationshipsViewProps) {
  const [relationships, setRelationships] = useState<RelationshipWithDetailsResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>("ALL");
  const [minConfidence, setMinConfidence] = useState<number>(0.0);
  const [crossDocOnly, setCrossDocOnly] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isReasoning, setIsReasoning] = useState(false);

  const fetchRelationships = () => {
    setLoading(true);
    api.getRelationships({
      datasetId,
      type: filterType !== "ALL" ? (filterType as RelationshipType) : undefined,
      minConfidence: minConfidence > 0 ? minConfidence : undefined,
      crossDocumentOnly: crossDocOnly,
      excludeSamePage: true,
    })
      .then((res) => setRelationships(res.relationships || []))
      .catch((err) => console.error("Failed to load relationships:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchRelationships();
  }, [datasetId, filterType, minConfidence, crossDocOnly, refreshTrigger]);

  const handleRunReasoning = async () => {
    if (!datasetId) return;
    setIsReasoning(true);
    try {
      await api.triggerReasoning(datasetId);
      fetchRelationships();
    } catch (err) {
      console.error("Failed to run reasoning:", err);
    } finally {
      setIsReasoning(false);
    }
  };

  // Client-side search filtering by metric, predicate, document name, or claim text
  const filteredRelationships = useMemo(() => {
    if (!searchQuery.trim()) return relationships;
    const q = searchQuery.toLowerCase().trim();
    return relationships.filter((rel) => {
      const matchDocA = rel.fact_a.document_filename?.toLowerCase().includes(q);
      const matchDocB = rel.fact_b.document_filename?.toLowerCase().includes(q);
      const matchPredA = rel.fact_a.predicate?.toLowerCase().includes(q);
      const matchPredB = rel.fact_b.predicate?.toLowerCase().includes(q);
      const matchClaimA = rel.fact_a.raw_value?.toLowerCase().includes(q);
      const matchClaimB = rel.fact_b.raw_value?.toLowerCase().includes(q);
      const matchEntityA = rel.fact_a.entity?.toLowerCase().includes(q);
      const matchEntityB = rel.fact_b.entity?.toLowerCase().includes(q);
      const matchRationale = rel.rationale?.toLowerCase().includes(q);

      return (
        matchDocA ||
        matchDocB ||
        matchPredA ||
        matchPredB ||
        matchClaimA ||
        matchClaimB ||
        matchEntityA ||
        matchEntityB ||
        matchRationale
      );
    });
  }, [relationships, searchQuery]);

  // Overall relationship stats
  const stats = useMemo(() => {
    return {
      total: relationships.length,
      corroborates: relationships.filter((r) => r.relationship_type === "CORROBORATES").length,
      contradicts: relationships.filter((r) => r.relationship_type === "CONTRADICTS").length,
      contextual: relationships.filter((r) => r.relationship_type === "CONTEXTUAL_DIFFERENCE").length,
      related: relationships.filter((r) => r.relationship_type === "RELATED").length,
    };
  }, [relationships]);

  const filterOptions = [
    { id: "ALL", label: "All Comparisons", icon: FileCheck2, count: stats.total, color: "text-foreground" },
    { id: "CORROBORATES", label: "Corroborates", icon: CheckCircle2, count: stats.corroborates, color: "text-emerald-500" },
    { id: "CONTRADICTS", label: "Contradicts", icon: AlertTriangle, count: stats.contradicts, color: "text-rose-500" },
    { id: "CONTEXTUAL_DIFFERENCE", label: "Contextual Diff", icon: Layers, count: stats.contextual, color: "text-amber-500" },
    { id: "RELATED", label: "Related", icon: Link2, count: stats.related, color: "text-sky-500" },
  ];

  return (
    <div className="space-y-5 animate-in fade-in duration-200">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-1">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-foreground">
              Cross-Document Relationship Reasoning
            </h2>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-primary/10 text-primary font-semibold border border-primary/20">
              Audit Engine
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-1 max-w-3xl leading-relaxed">
            Automated fact reconciliation comparing metrics across Annual Reports, Prospectuses, and Earnings Presentations with mathematical variance checks and source quote grounding.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button variant="outline" size="sm" onClick={fetchRelationships} className="h-8 text-xs font-medium">
            <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
            Refresh
          </Button>
          {datasetId && (
            <Button
              size="sm"
              onClick={handleRunReasoning}
              disabled={isReasoning}
              className="h-8 text-xs font-semibold shadow-sm"
            >
              <Play className="h-3.5 w-3.5 mr-1.5 fill-current" />
              {isReasoning ? "Reasoning..." : "Run Reasoning Pipeline"}
            </Button>
          )}
        </div>
      </div>

      {/* KPI Stats Overview Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl border border-border/80 bg-card/60 space-y-1">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Total Pairs</span>
            <Scale className="h-3.5 w-3.5 text-primary" />
          </div>
          <div className="text-2xl font-bold font-mono text-foreground">{stats.total}</div>
          <div className="text-[10px] text-muted-foreground">
            {crossDocOnly ? "Cross-document only" : "All relationships"}
          </div>
        </div>

        <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-500/[0.03] space-y-1">
          <div className="flex items-center justify-between text-xs text-emerald-400">
            <span>Corroborated</span>
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400">{stats.corroborates}</div>
          <div className="text-[10px] text-emerald-500/70">Verified matching facts</div>
        </div>

        <div className="p-3.5 rounded-xl border border-rose-500/30 bg-rose-500/[0.03] space-y-1">
          <div className="flex items-center justify-between text-xs text-rose-400">
            <span>Contradictions</span>
            <AlertTriangle className="h-3.5 w-3.5 text-rose-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-rose-400">{stats.contradicts}</div>
          <div className="text-[10px] text-rose-500/70">Direct variances / conflicts</div>
        </div>

        <div className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/[0.03] space-y-1">
          <div className="flex items-center justify-between text-xs text-amber-400">
            <span>Contextual Diffs</span>
            <Layers className="h-3.5 w-3.5 text-amber-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-400">{stats.contextual}</div>
          <div className="text-[10px] text-amber-500/70">Period / scope differences</div>
        </div>
      </div>

      {/* Control & Filter Bar */}
      <div className="p-3.5 rounded-xl border border-border bg-card/80 space-y-3 shadow-sm">
        {/* Top row: Scope Switch & Search Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Scope Toggle */}
          <div className="flex items-center p-1 rounded-lg bg-muted/70 border border-border/60 text-xs">
            <button
              onClick={() => setCrossDocOnly(true)}
              className={`px-3 py-1 rounded-md font-medium transition-all flex items-center gap-1.5 ${
                crossDocOnly
                  ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Scale className="h-3.5 w-3.5" />
              <span>Cross-Document Only (Recommended)</span>
            </button>
            <button
              onClick={() => setCrossDocOnly(false)}
              className={`px-3 py-1 rounded-md font-medium transition-all ${
                !crossDocOnly
                  ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span>Include Same-Document</span>
            </button>
          </div>

          {/* Search Box */}
          <div className="relative flex-1 sm:max-w-xs">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search metric (e.g. EBITDA), doc, or value..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 pl-8 pr-8 text-xs bg-background"
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

        {/* Bottom row: Type Filters & Confidence */}
        <div className="flex flex-wrap items-center justify-between gap-2.5 pt-1 border-t border-border/50">
          <div className="flex flex-wrap items-center gap-1.5">
            {filterOptions.map((opt) => {
              const Icon = opt.icon;
              const isSelected = filterType === opt.id;
              return (
                <button
                  key={opt.id}
                  onClick={() => setFilterType(opt.id)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
                    isSelected
                      ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                      : "bg-muted/60 text-muted-foreground hover:text-foreground hover:bg-muted"
                  }`}
                >
                  <Icon className={`h-3.5 w-3.5 ${isSelected ? "text-primary-foreground" : opt.color}`} />
                  <span>{opt.label}</span>
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${
                      isSelected ? "bg-primary-foreground/20 text-primary-foreground" : "bg-background text-muted-foreground"
                    }`}
                  >
                    {opt.count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Confidence Filter */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            <span>Min Confidence:</span>
            <select
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
              className="h-7 rounded border border-border bg-background px-2 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="0.0">All (0%)</option>
              <option value="0.6">≥ 60%</option>
              <option value="0.75">≥ 75%</option>
              <option value="0.9">≥ 90%</option>
            </select>
          </div>
        </div>
      </div>

      {/* Relationships List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
          <span>
            Showing <b className="text-foreground">{filteredRelationships.length}</b> verified relationship
            {filteredRelationships.length === 1 ? "" : "s"}
            {searchQuery && ` matching "${searchQuery}"`}
          </span>
          {crossDocOnly && (
            <span className="text-[11px] text-primary/90 flex items-center gap-1">
              <Scale className="h-3 w-3" />
              Trivial same-page table items excluded
            </span>
          )}
        </div>

        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-44 w-full rounded-2xl" />
            <Skeleton className="h-44 w-full rounded-2xl" />
            <Skeleton className="h-44 w-full rounded-2xl" />
          </div>
        ) : filteredRelationships.length > 0 ? (
          filteredRelationships.map((rel) => (
            <ComparisonCard
              key={rel.id}
              relationship={rel}
              onInspectFact={onInspectFact}
            />
          ))
        ) : (
          <EmptyState
            title="No Relationships Match Criteria"
            description={
              searchQuery
                ? `No relationships matched your search "${searchQuery}". Try clearing the search query or selecting "All Comparisons".`
                : "No cross-document relationships matched this filter. Try selecting 'All Comparisons' or lowering the confidence threshold."
            }
          />
        )}
      </div>
    </div>
  );
}
