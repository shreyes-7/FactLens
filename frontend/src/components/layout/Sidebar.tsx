import { useEffect, useState } from "react";
import {
  FileText,
  Search,
  GitCompare,
  ArrowRightLeft,
  Award,
  BarChart3,
  Sun,
  Moon,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { api } from "@/api/client";
import { HealthResponse } from "@/api/types";
import { Button } from "@/components/ui/button";

export type NavItem = "overview" | "documents" | "facts" | "compare" | "relationships" | "cases";

interface SidebarProps {
  activeView: NavItem;
  onSelectView: (view: NavItem) => void;
  isDark: boolean;
  onToggleTheme: () => void;
  documentCount: number;
  factCount: number;
  relationshipCount: number;
}

export function Sidebar({
  activeView,
  onSelectView,
  isDark,
  onToggleTheme,
  documentCount,
  factCount,
  relationshipCount,
}: SidebarProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    api.getHealth()
      .then(setHealth)
      .catch((err) => console.warn("Failed to fetch health:", err));
  }, []);

  const navItems = [
    {
      id: "overview" as NavItem,
      label: "Overview",
      icon: BarChart3,
      count: null,
    },
    {
      id: "documents" as NavItem,
      label: "Documents",
      icon: FileText,
      count: documentCount,
    },
    {
      id: "facts" as NavItem,
      label: "Fact Explorer",
      icon: Search,
      count: factCount,
    },
    {
      id: "compare" as NavItem,
      label: "Compare Documents",
      icon: ArrowRightLeft,
      count: null,
      badge: "What Changed?",
    },
    {
      id: "relationships" as NavItem,
      label: "Relationships",
      icon: GitCompare,
      count: relationshipCount,
    },
    {
      id: "cases" as NavItem,
      label: "Assignment Cases",
      icon: Award,
      badge: "4 Cases",
      highlight: true,
    },
  ];

  return (
    <aside className="w-64 border-r border-border bg-card/60 backdrop-blur-md flex flex-col justify-between h-screen sticky top-0 select-none">
      {/* Top: Branding & Navigation */}
      <div>
        {/* Brand Header */}
        <div className="p-5 border-b border-border/60 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shadow-sm">
              <Zap className="h-4 w-4 fill-primary/30" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-foreground flex items-center gap-1.5">
                FactLens
                <span className="text-[10px] font-mono font-normal px-1.5 py-0.2 rounded bg-muted text-muted-foreground border border-border/50">
                  v0.1
                </span>
              </h1>
              <p className="text-[10px] text-muted-foreground truncate">
                Evidence Fact Knowledge Layer
              </p>
            </div>
          </div>
        </div>

        {/* Nav Links */}
        <div className="p-3 space-y-1">
          <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
            Workspace
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectView(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm font-semibold"
                    : "text-muted-foreground hover:bg-muted/70 hover:text-foreground"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`h-4 w-4 ${isActive ? "text-primary-foreground" : "text-muted-foreground"}`} />
                  <span>{item.label}</span>
                </div>
                {item.count !== null && item.count !== undefined && item.count > 0 && (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.2 rounded ${
                      isActive
                        ? "bg-primary-foreground/20 text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {item.count}
                  </span>
                )}
                {item.badge && (
                  <span
                    className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${
                      isActive
                        ? "bg-primary-foreground/20 text-primary-foreground border-transparent"
                        : "bg-emerald-500/10 text-emerald-500 border-emerald-500/25"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Bottom: System Diagnostics & Theme */}
      <div className="p-3 border-t border-border/60 space-y-3">
        {/* System Diagnostics */}
        <div className="p-2.5 rounded-lg border border-border/50 bg-muted/30 text-[11px] space-y-2">
          <div className="flex items-center justify-between pb-1 border-b border-border/40">
            <div className="flex items-center gap-1.5 text-foreground/90 font-semibold">
              <span className={`h-2 w-2 rounded-full ${health?.database_connected ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
              <span>FastAPI Backend</span>
            </div>
            <span className="text-[10px] font-mono text-emerald-500 font-medium">
              {health?.status === "ok" ? "200 OK" : "Connecting..."}
            </span>
          </div>

          <div className="space-y-1 pt-0.5 text-[10px]">
            <div className="flex items-center justify-between gap-1 text-muted-foreground">
              <span className="font-medium text-foreground/70">Primary Model</span>
              <span className="font-mono text-sky-400 font-semibold truncate max-w-[120px]" title={health?.primary_model || "gemini"}>
                {health?.primary_model ? `Gemini · ${health.primary_model}` : "Gemini Flash"}
              </span>
            </div>
            <div className="flex items-center justify-between gap-1 text-muted-foreground">
              <span className="font-medium text-foreground/70">Fallback Model</span>
              <span className="font-mono text-amber-400 font-medium truncate max-w-[120px]" title={health?.fallback_model || "groq"}>
                {health?.fallback_model ? `Groq · ${health.fallback_model}` : "Groq Fallback"}
              </span>
            </div>
            <div className="flex items-center justify-between pt-1 border-t border-border/30 text-muted-foreground">
              <span>Zero-Downtime</span>
              <span className="text-emerald-500 font-mono font-medium flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {health?.fallback_enabled ? "Groq Standby" : "Disabled"}
              </span>
            </div>
          </div>
        </div>

        {/* Theme Toggle & Info */}
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <ShieldCheck className="h-3.5 w-3.5 text-primary/70" />
            <span>Grounded Evidence</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleTheme}
            className="h-7 w-7 text-muted-foreground hover:text-foreground"
            title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {isDark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
          </Button>
        </div>
      </div>
    </aside>
  );
}
