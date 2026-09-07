import { CheckCircle2, Loader2, AlertCircle, X } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface ActiveTask {
  id: string;
  type: "extraction" | "upload";
  title: string;
  subtitle?: string;
  status: "running" | "completed" | "error";
  error?: string;
  stats?: {
    facts?: number;
    relationships?: number;
    chunks?: number;
    pages?: number;
  };
}

interface ActiveTaskBannerProps {
  task: ActiveTask | null;
  onDismiss: () => void;
}

export function ActiveTaskBanner({ task, onDismiss }: ActiveTaskBannerProps) {
  if (!task) return null;

  return (
    <aside
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="fixed bottom-6 right-6 z-50 max-w-md w-full animate-in slide-in-from-bottom-5 fade-in duration-200"
    >
      <div
        className={`p-4 rounded-xl border shadow-xl backdrop-blur-md transition-all ${
          task.status === "running"
            ? "bg-card/95 border-primary/40 shadow-primary/10 ring-1 ring-primary/20"
            : task.status === "completed"
            ? "bg-card/95 border-emerald-500/40 shadow-emerald-500/10 ring-1 ring-emerald-500/20"
            : "bg-card/95 border-rose-500/40 shadow-rose-500/10"
        }`}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div
              className={`h-9 w-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                task.status === "running"
                  ? "bg-primary/10 text-primary animate-pulse"
                  : task.status === "completed"
                  ? "bg-emerald-500/10 text-emerald-500"
                  : "bg-rose-500/10 text-rose-500"
              }`}
            >
              {task.status === "running" ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : task.status === "completed" ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
              ) : (
                <AlertCircle className="h-5 w-5 text-rose-500" />
              )}
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h4 className="text-xs font-semibold text-foreground tracking-tight">
                  {task.title}
                </h4>
                <span
                  className={`text-[9px] font-mono font-medium px-1.5 py-0.2 rounded uppercase ${
                    task.status === "running"
                      ? "bg-primary/15 text-primary"
                      : task.status === "completed"
                      ? "bg-emerald-500/15 text-emerald-500"
                      : "bg-rose-500/15 text-rose-500"
                  }`}
                >
                  {task.status === "running" ? "Processing" : task.status}
                </span>
              </div>

              {task.subtitle && (
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  {task.subtitle}
                </p>
              )}

              {task.status === "running" && (
                <div className="w-full bg-muted/60 h-1.5 rounded-full overflow-hidden mt-2">
                  <div className="h-full bg-primary animate-pulse w-3/4 rounded-full" />
                </div>
              )}

              {task.status === "completed" && task.stats && (
                <div className="flex items-center gap-3 pt-1 text-[10px] font-mono text-muted-foreground">
                  {task.stats.facts !== undefined && (
                    <span>
                      Facts: <b className="text-emerald-500 font-bold">+{task.stats.facts}</b>
                    </span>
                  )}
                  {task.stats.chunks !== undefined && (
                    <span>
                      Chunks: <b className="text-foreground">{task.stats.chunks}</b>
                    </span>
                  )}
                  {task.stats.pages !== undefined && (
                    <span>
                      Pages: <b className="text-foreground">{task.stats.pages}</b>
                    </span>
                  )}
                </div>
              )}

              {task.error && (
                <p className="text-[11px] text-rose-500 pt-0.5">
                  {task.error}
                </p>
              )}
            </div>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={onDismiss}
            className="h-6 w-6 text-muted-foreground hover:text-foreground shrink-0 -mr-1 -mt-1"
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </aside>
  );
}
