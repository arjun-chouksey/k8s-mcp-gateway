import { CheckCircle2, CircleDashed, ShieldCheck, TriangleAlert } from "lucide-react";
import type { ToolTrace } from "../lib/types";
import { cn } from "../lib/utils";

export function ToolCallCard({ trace }: { trace: ToolTrace }) {
  const pending = trace.outcome === "running";
  const ok = trace.outcome === "ok";
  const Icon = pending ? CircleDashed : ok ? CheckCircle2 : TriangleAlert;
  return <article className="border-l-2 border-zinc-700 bg-zinc-950/60 px-3 py-2.5" aria-label={`Tool call ${trace.name}`}>
    <div className="flex flex-wrap items-center gap-2">
      <Icon className={cn("size-4", pending && "animate-spin text-amber-300", ok && "text-emerald-400", !pending && !ok && "text-rose-400")} />
      <code className="text-xs font-medium text-zinc-200">{trace.name}</code>
      <span className="ml-auto text-[10px] uppercase tracking-[.14em] text-zinc-500">{pending ? "Running" : trace.outcome.replaceAll("_", " ")}</span>
      {trace.duration_ms !== undefined ? <span className="font-mono text-[11px] text-zinc-500">{trace.duration_ms} ms</span> : null}
    </div>
    <p className="mt-2 flex items-center gap-1.5 text-[11px] text-zinc-500"><ShieldCheck className="size-3" />Arguments and sensitive result fields are hidden.</p>
  </article>;
}
