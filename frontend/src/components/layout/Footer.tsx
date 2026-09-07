import { Github, Mail, ShieldCheck, Zap } from "lucide-react";

export function Footer() {
  return (
    <footer className="w-full border-t border-border/60 bg-card/40 backdrop-blur-sm mt-auto py-5 px-6 text-xs text-muted-foreground select-none">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Brand & Author */}
        <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-4 text-center sm:text-left">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shadow-sm">
              <Zap className="h-3.5 w-3.5 fill-primary/30" />
            </div>
            <span className="font-semibold text-foreground tracking-tight">FactLens</span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-muted text-muted-foreground border border-border/40">
              v0.1
            </span>
          </div>
          <span className="hidden sm:inline text-border">•</span>
          <span className="text-[11px] text-muted-foreground/90">
            Evidence-Grounded Cross-Document Fact Verification Engine
          </span>
        </div>

        {/* Links & Contacts */}
        <div className="flex flex-wrap items-center justify-center gap-4 text-[11px]">
          <a
            href="https://github.com/shreyes-7/FactLens"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 hover:text-foreground transition-colors font-medium text-foreground/80 hover:underline"
            title="FactLens GitHub Repository"
          >
            <Github className="h-3.5 w-3.5" />
            <span>shreyes-7/FactLens</span>
          </a>

          <span className="text-border">•</span>

          <a
            href="mailto:shreyesjaiswal7@gmail.com"
            className="flex items-center gap-1.5 hover:text-foreground transition-colors font-medium text-foreground/80 hover:underline"
            title="Contact Shreyes Jaiswal"
          >
            <Mail className="h-3.5 w-3.5 text-primary/80" />
            <span>shreyesjaiswal7@gmail.com</span>
          </a>

          <span className="text-border">•</span>

          <div className="flex items-center gap-1 text-[11px] text-emerald-500/90 font-medium">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>Character-Level Grounded</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
