import { Upload, Database, Award } from "lucide-react";
import { Button } from "@/components/ui/button";

import { DatasetResponse } from "@/api/types";

interface HeaderProps {
  datasetName?: string;
  datasets?: DatasetResponse[];
  selectedDatasetId?: string;
  totalFacts?: number;
  onSelectDataset?: (id: string) => void;
  onOpenUpload: () => void;
  onOpenCases: () => void;
}

export function Header({
  datasetName,
  datasets = [],
  selectedDatasetId = "all",
  totalFacts = 0,
  onSelectDataset = () => {},
  onOpenUpload,
  onOpenCases,
}: HeaderProps) {
  return (
    <header className="h-14 border-b border-border/80 bg-background/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Active Dataset Dropdown */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border/60 bg-muted/40 text-xs font-medium text-foreground/90">
          <Database className="h-3.5 w-3.5 text-primary/80" />
          <span className="text-muted-foreground">Dataset:</span>
          {datasets.length > 0 ? (
            <select
              value={selectedDatasetId || "all"}
              onChange={(e) => onSelectDataset(e.target.value)}
              className="bg-transparent border-0 font-semibold text-foreground cursor-pointer focus:outline-none focus:ring-0 text-xs py-0 pl-1 pr-4"
            >
              <option value="all" className="bg-card text-foreground">
                All Datasets ({totalFacts} facts)
              </option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id} className="bg-card text-foreground">
                  {d.name} ({d.fact_count} facts, {d.document_count} docs)
                </option>
              ))}
            </select>
          ) : (
            <span className="font-semibold text-foreground">{datasetName || "Delhivery Financials"}</span>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-2.5">
        <Button
          variant="outline"
          size="sm"
          onClick={onOpenCases}
          className="h-8 text-xs font-medium border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/10 hover:text-emerald-400"
        >
          <Award className="h-3.5 w-3.5 mr-1.5" />
          Assignment Cases
        </Button>
        <Button
          size="sm"
          onClick={onOpenUpload}
          className="h-8 text-xs font-medium shadow-sm bg-primary hover:bg-primary/90 text-primary-foreground"
        >
          <Upload className="h-3.5 w-3.5 mr-1.5" />
          Upload PDF
        </Button>
      </div>
    </header>
  );
}
