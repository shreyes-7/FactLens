import React, { useState, useRef, useEffect } from "react";
import { Upload, FileUp, CheckCircle, AlertCircle, Loader2, Database } from "lucide-react";
import { api } from "@/api/client";
import { DatasetResponse } from "@/api/types";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { formatBytes } from "@/lib/formatters";

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  datasetId?: string;
  onUploadSuccess: () => void;
}

export function DocumentUploadModal({
  isOpen,
  onClose,
  datasetId,
  onUploadSuccess,
}: DocumentUploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [datasets, setDatasets] = useState<DatasetResponse[]>([]);
  const [targetDatasetId, setTargetDatasetId] = useState<string>("");
  const [newDatasetName, setNewDatasetName] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      api.getDatasets()
        .then((ds) => {
          setDatasets(ds);
          if (datasetId && datasetId !== "all") {
            setTargetDatasetId(datasetId);
          } else if (ds.length > 0) {
            setTargetDatasetId(ds[0].id);
          }
        })
        .catch(console.error);
    }
  }, [isOpen, datasetId]);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      validateAndSetFile(droppedFile);
    }
  };

  const validateAndSetFile = (f: File) => {
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files (.pdf) are supported.");
      return;
    }
    setError(null);
    setFile(f);
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    setError(null);
    try {
      let finalDatasetId = targetDatasetId;
      if (targetDatasetId === "NEW") {
        if (!newDatasetName.trim()) {
          setError("Please enter a name for the new dataset.");
          setIsUploading(false);
          return;
        }
        const newDs = await api.createDataset(newDatasetName.trim());
        finalDatasetId = newDs.id;
      }

      const resp = await api.uploadDocument(file, finalDatasetId || undefined);
      setSuccessMessage(
        resp.is_duplicate
          ? `File '${file.name}' already ingested (${resp.pages_extracted} pages verified).`
          : `Ingested '${file.name}' with ${resp.pages_extracted} pages successfully.`
      );
      setTimeout(() => {
        setIsUploading(false);
        setFile(null);
        setSuccessMessage(null);
        onUploadSuccess();
        onClose();
      }, 1500);
    } catch (err: any) {
      setIsUploading(false);
      setError(err.message || "Failed to upload document.");
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Upload PDF Document"
      description="Ingest a new PDF to extract pages and prepare for evidence-grounded fact extraction."
    >
      <div className="space-y-4 pt-2">
        {/* Target Dataset Selection */}
        <div className="p-3 rounded-lg border border-border/70 bg-muted/20 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
            <Database className="h-3.5 w-3.5 text-primary" />
            <span>Target Dataset</span>
          </div>
          <select
            value={targetDatasetId}
            onChange={(e) => setTargetDatasetId(e.target.value)}
            disabled={isUploading}
            className="w-full h-8 px-2.5 rounded-md border border-input bg-background text-xs font-medium text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.document_count ?? 0} docs, {d.fact_count ?? 0} facts)
              </option>
            ))}
            <option value="NEW">+ Create New Dataset...</option>
          </select>

          {targetDatasetId === "NEW" && (
            <input
              type="text"
              placeholder="e.g. india-macroeconomy"
              value={newDatasetName}
              onChange={(e) => setNewDatasetName(e.target.value)}
              disabled={isUploading}
              className="w-full h-8 px-2.5 rounded-md border border-input bg-background text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          )}
        </div>
        {/* Dropzone */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleFileDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
            isDragging
              ? "border-primary bg-primary/5"
              : file
              ? "border-emerald-500/50 bg-emerald-500/5"
              : "border-border hover:border-primary/50 hover:bg-muted/30"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                validateAndSetFile(e.target.files[0]);
              }
            }}
          />
          {file ? (
            <div className="flex flex-col items-center">
              <FileUp className="h-8 w-8 text-emerald-500 mb-2" />
              <p className="text-sm font-semibold text-foreground truncate max-w-xs">{file.name}</p>
              <p className="text-xs text-muted-foreground mt-1">{formatBytes(file.size)}</p>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <Upload className="h-8 w-8 text-muted-foreground mb-2" />
              <p className="text-sm font-medium text-foreground">
                Drop your PDF here, or <span className="text-primary underline">browse</span>
              </p>
              <p className="text-xs text-muted-foreground mt-1">PDF documents up to 50MB</p>
            </div>
          )}
        </div>

        {/* Status messages */}
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-500 text-xs">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMessage && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-500 text-xs">
            <CheckCircle className="h-4 w-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Buttons */}
        <div className="flex items-center justify-end gap-2 pt-2">
          <Button variant="outline" size="sm" onClick={onClose} disabled={isUploading}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleUpload}
            disabled={!file || isUploading}
            className="shadow-sm"
          >
            {isUploading ? (
              <>
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                Ingesting...
              </>
            ) : (
              "Ingest Document"
            )}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
