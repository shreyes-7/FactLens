import { useState, useEffect } from "react";
import { Sidebar, NavItem } from "./Sidebar";
import { Header } from "./Header";
import { OverviewView } from "@/views/OverviewView";
import { DocumentsView } from "@/views/DocumentsView";
import { FactsView } from "@/views/FactsView";
import { RelationshipsView } from "@/views/RelationshipsView";
import { CasesView } from "@/views/CasesView";
import { DocumentUploadModal } from "@/components/documents/DocumentUploadModal";
import { api } from "@/api/client";
import { DatasetResponse } from "@/api/types";

export function AppShell() {
  const [activeView, setActiveView] = useState<NavItem>("overview");
  const [isDark, setIsDark] = useState<boolean>(true);
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [datasets, setDatasets] = useState<DatasetResponse[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("all");
  const [inspectFactId, setInspectFactId] = useState<string | null>(null);

  // Sync dark class on html root
  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [isDark]);

  const fetchDatasets = () => {
    api.getDatasets()
      .then((data) => {
        setDatasets(data);
        // If current selection is invalid or only one dataset exists, stay smart
        if (data.length > 0 && selectedDatasetId !== "all") {
          const exists = data.some((d) => d.id === selectedDatasetId);
          if (!exists) setSelectedDatasetId("all");
        }
      })
      .catch((err) => console.error("Error loading datasets:", err));
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const activeDataset = datasets.find((d) => d.id === selectedDatasetId);
  const totalDocs = datasets.reduce((sum, d) => sum + (d.document_count || 0), 0);
  const totalFacts = datasets.reduce((sum, d) => sum + (d.fact_count || 0), 0);
  const totalRelationships = datasets.reduce((sum, d) => sum + (d.relationship_count || 0), 0);

  const currentDatasetId = selectedDatasetId === "all" ? undefined : selectedDatasetId;

  const handleInspectFact = (factId: string) => {
    setInspectFactId(factId);
    setActiveView("facts");
  };

  return (
    <div className="min-h-screen flex bg-background text-foreground antialiased selection:bg-primary/20 selection:text-primary">
      {/* Sidebar */}
      <Sidebar
        activeView={activeView}
        onSelectView={(v) => {
          setActiveView(v);
          setInspectFactId(null);
        }}
        isDark={isDark}
        onToggleTheme={() => setIsDark(!isDark)}
        documentCount={activeDataset ? activeDataset.document_count : totalDocs}
        factCount={activeDataset ? activeDataset.fact_count : totalFacts}
        relationshipCount={activeDataset ? activeDataset.relationship_count : totalRelationships}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          datasetName={activeDataset?.name}
          datasets={datasets}
          selectedDatasetId={selectedDatasetId}
          totalFacts={totalFacts}
          onSelectDataset={(id) => setSelectedDatasetId(id)}
          onOpenUpload={() => setIsUploadOpen(true)}
          onOpenCases={() => setActiveView("cases")}
        />

        <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
          {activeView === "overview" && (
            <OverviewView
              onNavigate={(v) => setActiveView(v)}
              onOpenUpload={() => setIsUploadOpen(true)}
            />
          )}

          {activeView === "documents" && (
            <DocumentsView
              onOpenUpload={() => setIsUploadOpen(true)}
              datasetId={currentDatasetId}
              onRefreshCounts={fetchDatasets}
            />
          )}

          {activeView === "facts" && (
            <FactsView
              datasetId={currentDatasetId}
              initialFactId={inspectFactId}
            />
          )}

          {activeView === "relationships" && (
            <RelationshipsView
              datasetId={currentDatasetId}
              onInspectFact={handleInspectFact}
            />
          )}

          {activeView === "cases" && <CasesView />}
        </main>
      </div>

      {/* Upload PDF Modal */}
      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        datasetId={activeDataset?.id}
        onUploadSuccess={() => {
          fetchDatasets();
          setActiveView("documents");
        }}
      />
    </div>
  );
}
