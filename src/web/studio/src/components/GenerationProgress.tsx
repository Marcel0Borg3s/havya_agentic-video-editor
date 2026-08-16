"use client";

import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { useJobStore } from "@/stores/jobStore";

const stages = [
  "Analisando material",
  "Planejando edição",
  "Refinando cortes",
  "Renderizando vídeo",
  "Revisando resultado",
];

function currentStage(lines: string[]): number {
  const text = lines.join("\n").toLowerCase();
  if (text.includes("reviewer")) return 4;
  if (text.includes("editor")) return 3;
  if (text.includes("trim_refiner")) return 2;
  if (text.includes("director")) return 1;
  if (text.includes("preprocess")) return 0;
  return 0;
}

export function GenerationProgress() {
  const status = useJobStore((s) => s.pipelineStatus);
  const lines = useJobStore((s) => s.progressLines.map((entry) => entry.line));
  const error = useJobStore((s) => s.error);
  const active = currentStage(lines);
  const percent = status === "completed" ? 100 : Math.max(8, Math.round(((active + 1) / stages.length) * 100));

  if (status === "idle") return null;

  return (
    <div className="fixed bottom-4 right-4 z-40 w-80 rounded-xl border border-border bg-surface p-4 shadow-2xl">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold">Progresso da geração</span>
        <span className="text-xs text-muted">{percent}%</span>
      </div>
      <div className="h-2 rounded-full bg-border overflow-hidden mb-4">
        <div className={`h-full transition-all ${status === "failed" ? "bg-destructive" : "bg-accent"}`} style={{ width: `${percent}%` }} />
      </div>
      <div className="space-y-2">
        {stages.map((stage, index) => {
          const done = status === "completed" || index < active;
          const current = status === "running" && index === active;
          return <div key={stage} className="flex items-center gap-2 text-xs">
            {done ? <CheckCircle2 className="w-4 h-4 text-accent" /> : current ? <Loader2 className="w-4 h-4 text-amber-400 animate-spin" /> : <span className="w-4 h-4 rounded-full border border-border" />}
            <span className={current ? "text-foreground" : "text-muted"}>{stage}</span>
          </div>;
        })}
      </div>
      {status === "failed" && <div className="mt-3 flex gap-2 text-xs text-destructive"><XCircle className="w-4 h-4 shrink-0" />{error || "A geração falhou."}</div>}
    </div>
  );
}

export { currentStage };

// Keep the progress component independent from the timeline/editor layout.
// It can later be reused by a dedicated generation page.
void currentStage;
void CheckCircle2;
void XCircle;
