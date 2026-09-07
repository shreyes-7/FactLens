import { useEffect, useState } from "react";
import { Play, Sparkles, RefreshCw, Layers, CheckCircle2, AlertTriangle, Link2, HelpCircle } from "lucide-react";
import { api } from "@/api/client";
import { RelationshipWithDetailsResponse, RelationshipType } from "@/api/types";
import { Button } from "@/components/ui/button";
import { ComparisonCard } from "@/components/relationships/ComparisonCard";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";

interface RelationshipsViewProps {
  datasetId?: string;
  onInspectFact?: (factId: string) => void;
}

export function RelationshipsView({ datasetId, onInspectFact }: RelationshipsViewProps) {
  const [relationships, setRelationships] = useState<RelationshipWithDetailsResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>("ALL");
  const [minConfidence, setMinConfidence] = useState<number>(0.0);
  const [isReasoning, setIsReasoning] = useState(false);

  const fetchRelationships = () => {
    setLoading(true);
    api.getRelationships({
      datasetId,
      type: filterType !== "ALL" ? (filterType as RelationshipType) : undefined,
      minConfidence: minConfidence > 0 ? minConfidence : undefined,
    })
      .then((res) => setRelationships(res.relationships || []))
      .catch((err) => console.error("Failed to load relationships:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchRelationships();
  }, [datasetId, filterType, minConfidence]);

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

  const filterOptions = [
    { id: "ALL", label: "All Types", icon: null, count: relationships.length },
    { id: "CORROBORATES", label: "Corroborates", icon: CheckCircle2, color: "text-emerald-500" },
    { id: "CONTRADICTS", label: "Contradicts", icon: AlertTriangle, color: "text-rose-500" },
    { id: "CONTEXTUAL_DIFFERENCE", label: "Contextual Diff", icon: Layers, color: "text-amber-500" },
    { id: "RELATED", label: "Related", icon: Link2, color: "text-sky-500" },
    { id: "UNCERTAIN", label: "Uncertain", icon: HelpCircle, color: "text-zinc-500" },
  ];

  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-foreground">Cross-Document Relationship Reasoning</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Compare pairs of facts across different PDF reports with automated variance math and contextual analysis.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchRelationships} className="h-8 text-xs">
            <RefreshCw className="h-3 w-3 mr-1" />
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

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl border border-border bg-card/60">
        <div className="flex flex-wrap items-center gap-1.5">
          {filterOptions.map((opt) => {
            const Icon = opt.icon;
            const isSelected = filterType === opt.id;
            return (
              <button
                key={opt.id}
                onClick={() => setFilterType(opt.id)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
                  isSelected
                    ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                    : "bg-muted text-muted-foreground hover:text-foreground"
                }`}
              >
                {Icon && <Icon className={`h-3.5 w-3.5 ${isSelected ? "text-primary-foreground" : opt.color}`} />}
                <span>{opt.label}</span>
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
            className="h-7 rounded border border-border bg-background px-2 text-xs font-mono text-foreground"
          >
            <option value="0.0">All (0%)</option>
            <option value="0.6">≥ 60%</option>
            <option value="0.75">≥ 75%</option>
            <option value="0.9">≥ 90%</option>
          </select>
        </div>
      </div>

      {/* Relationships Grid */}
      <div className="space-y-4">
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-36 w-full rounded-xl" />
            <Skeleton className="h-36 w-full rounded-xl" />
            <Skeleton className="h-36 w-full rounded-xl" />
          </div>
        ) : relationships.length > 0 ? (
          relationships.map((rel) => (
            <ComparisonCard
              key={rel.id}
              relationship={rel}
              onInspectFact={onInspectFact}
            />
          ))
        ) : (
          <EmptyState
            title="No Relationships Match Criteria"
            description="No cross-document relationships matched this filter. Try selecting 'All Types' or lowering the confidence threshold."
          />
        )}
      </div>
    </div>
  );
}
