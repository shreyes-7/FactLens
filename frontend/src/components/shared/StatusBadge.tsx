import { Badge } from "@/components/ui/badge";
import { RelationshipType } from "@/api/types";
import { CheckCircle2, AlertTriangle, HelpCircle, Layers, Link2 } from "lucide-react";

export function RelationshipBadge({
  type,
  className,
}: {
  type: RelationshipType | string;
  className?: string;
}) {
  switch (type) {
    case "CORROBORATES":
      return (
        <Badge variant="corroborates" className={className}>
          <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-500 inline" />
          Corroborates
        </Badge>
      );
    case "CONTRADICTS":
      return (
        <Badge variant="contradicts" className={className}>
          <AlertTriangle className="w-3 h-3 mr-1 text-rose-500 inline" />
          Contradicts
        </Badge>
      );
    case "CONTEXTUAL_DIFFERENCE":
      return (
        <Badge variant="contextual" className={className}>
          <Layers className="w-3 h-3 mr-1 text-amber-500 inline" />
          Contextual Difference
        </Badge>
      );
    case "RELATED":
      return (
        <Badge variant="related" className={className}>
          <Link2 className="w-3 h-3 mr-1 text-sky-500 inline" />
          Related
        </Badge>
      );
    case "UNCERTAIN":
    default:
      return (
        <Badge variant="uncertain" className={className}>
          <HelpCircle className="w-3 h-3 mr-1 text-zinc-500 inline" />
          Uncertain
        </Badge>
      );
  }
}

export function ProcessingStatusBadge({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  const norm = status.toLowerCase();
  if (norm === "completed") {
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 ${className}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5 animate-pulse" />
        Completed
      </span>
    );
  }
  if (norm === "processing" || norm === "processing_queued") {
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-500/10 text-amber-500 border border-amber-500/20 ${className}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mr-1.5 animate-ping" />
        Processing
      </span>
    );
  }
  if (norm === "failed") {
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-rose-500/10 text-rose-500 border border-rose-500/20 ${className}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-rose-500 mr-1.5" />
        Failed
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-500/10 text-zinc-400 border border-zinc-500/20 ${className}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 mr-1.5" />
      Ingested
    </span>
  );
}
