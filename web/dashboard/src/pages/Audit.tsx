import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ChevronLeft, ChevronRight, Clock3, RefreshCw, ScrollText } from "lucide-react";
import { useState } from "react";
import { Button } from "../components/Button";
import { api } from "../lib/api";
import type { Actor, AuditOutcome, ServerStatus } from "../lib/types";

const PAGE_SIZE = 20;
const dateTime = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "medium" });
const outcomes: Array<{ value: "" | AuditOutcome; label: string }> = [
  { value: "", label: "All outcomes" }, { value: "ok", label: "Succeeded" },
  { value: "tool_error", label: "Tool error" }, { value: "upstream_error", label: "Upstream error" },
  { value: "timeout", label: "Timed out" }, { value: "denied", label: "Denied" },
];
const outcomeStyle: Record<AuditOutcome, string> = {
  ok: "border-emerald-900/60 bg-emerald-950/30 text-emerald-400",
  tool_error: "border-amber-900/60 bg-amber-950/30 text-amber-300",
  upstream_error: "border-red-900/60 bg-red-950/30 text-red-300",
  timeout: "border-orange-900/60 bg-orange-950/30 text-orange-300",
  denied: "border-zinc-700 bg-zinc-900 text-zinc-400",
};
const statusStyle: Record<ServerStatus, string> = {
  connected: "text-emerald-400", unreachable: "text-red-400", disabled: "text-zinc-500", checking: "text-amber-300",
};

function iso(value: string) { return value ? new Date(value).toISOString() : undefined; }

export function Audit({ actor }: { actor: Actor }) {
  const [server, setServer] = useState(""); const [outcome, setOutcome] = useState<"" | AuditOutcome>("");
  const [user, setUser] = useState(""); const [after, setAfter] = useState(""); const [before, setBefore] = useState(""); const [offset, setOffset] = useState(0);
  const servers = useQuery({ queryKey: ["servers"], queryFn: api.servers, refetchInterval: 10_000 });
  const members = useQuery({ queryKey: ["members"], queryFn: api.members, enabled: actor.role === "admin" });
  const filters = { user: actor.role === "admin" ? user || undefined : undefined, server: server || undefined, outcome: outcome || undefined, started_after: iso(after), started_before: iso(before), limit: PAGE_SIZE, offset };
  const audit = useQuery({ queryKey: ["audit", filters], queryFn: () => api.audit(filters), refetchInterval: 10_000 });
  const memberNames = new Map(members.data?.map((member) => [member.id, member.email]));
  function resetPage(setter: (value: string) => void, value: string) { setOffset(0); setter(value); }
  async function refresh() { await Promise.all([audit.refetch(), servers.refetch()]); }
  return <section className="mx-auto max-w-7xl px-4 py-7 sm:px-6 lg:px-10 lg:py-9">
    <header className="mb-8 flex flex-col gap-5 border-b border-zinc-800 pb-7 sm:flex-row sm:items-end sm:justify-between"><div><p className="mb-2 font-mono text-[11px] uppercase tracking-[.16em] text-zinc-500">Operations / Evidence</p><h1 className="text-2xl font-semibold tracking-tight">Audit logs</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">Tool calls and upstream health refresh every 10 seconds. Results reflect gateway records, not browser-side probes.</p></div><Button onClick={() => void refresh()} busy={audit.isFetching || servers.isFetching}><RefreshCw className="size-4" />Refresh</Button></header>
    <div className="mb-7 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{servers.isError ? <div className="col-span-full rounded-md border border-red-900/50 bg-red-950/20 p-4 text-sm text-red-300">Server status could not be loaded.</div> : servers.data?.map((item) => <article key={item.id} className="rounded-lg border border-zinc-800 bg-[#18181B] p-4"><div className="flex items-start justify-between gap-3"><div><h2 className="text-sm font-medium">{item.display_name}</h2><p className="mt-1 font-mono text-[11px] text-zinc-500">{item.slug}</p></div><span className={`text-xs font-medium capitalize ${statusStyle[item.status]}`}>{item.status}</span></div><div className="mt-4 flex items-center justify-between text-xs text-zinc-500"><span>{item.tool_count} tools</span><span>{item.last_checked_at ? dateTime.format(new Date(item.last_checked_at)) : "Not checked"}</span></div>{item.last_error ? <p className="mt-3 flex gap-2 border-t border-zinc-800 pt-3 text-xs leading-5 text-red-300"><AlertTriangle className="mt-0.5 size-3.5 shrink-0" />{item.last_error}</p> : null}</article>)}</div>
    <div className="mb-5 grid gap-3 rounded-lg border border-zinc-800 bg-[#18181B] p-4 md:grid-cols-2 xl:grid-cols-5" aria-label="Audit filters">
      {actor.role === "admin" ? <label className="text-xs text-zinc-500">User<select className="mt-2 min-h-10 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm text-zinc-200" value={user} onChange={(event) => resetPage(setUser, event.target.value)}><option value="">All users</option>{members.data?.map((member) => <option key={member.id} value={member.id}>{member.email}</option>)}</select></label> : null}
      <label className="text-xs text-zinc-500">Server<select className="mt-2 min-h-10 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm text-zinc-200" value={server} onChange={(event) => resetPage(setServer, event.target.value)}><option value="">All servers</option>{servers.data?.map((item) => <option key={item.id} value={item.slug}>{item.display_name}</option>)}</select></label>
      <label className="text-xs text-zinc-500">Outcome<select className="mt-2 min-h-10 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm text-zinc-200" value={outcome} onChange={(event) => { setOffset(0); setOutcome(event.target.value as "" | AuditOutcome); }}>{outcomes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
      <label className="text-xs text-zinc-500">From<input type="datetime-local" className="mt-2 min-h-10 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm text-zinc-200" value={after} max={before || undefined} onChange={(event) => resetPage(setAfter, event.target.value)} /></label>
      <label className="text-xs text-zinc-500">Until<input type="datetime-local" className="mt-2 min-h-10 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm text-zinc-200" value={before} min={after || undefined} onChange={(event) => resetPage(setBefore, event.target.value)} /></label>
    </div>
    {audit.isPending ? <p className="py-16 text-center text-sm text-zinc-500">Loading audit events…</p> : audit.isError ? <div className="rounded-md border border-red-900/50 bg-red-950/20 p-4 text-sm text-red-300">Audit events could not be loaded. Check the filters and try again.</div> : audit.data.items.length === 0 ? <div className="grid min-h-56 place-content-center justify-items-center rounded-lg border border-dashed border-zinc-800 text-center"><ScrollText className="mb-4 size-6 text-zinc-600" /><h2 className="text-sm font-medium">No matching tool calls</h2><p className="mt-2 text-xs text-zinc-500">Change the filters or invoke a gateway tool.</p></div> : <div className="overflow-hidden rounded-lg border border-zinc-800 bg-[#18181B]"><div className="hidden grid-cols-[180px_1fr_130px_120px_100px] gap-4 border-b border-zinc-800 bg-zinc-950/40 px-5 py-3 text-[10px] uppercase tracking-wider text-zinc-600 lg:grid"><span>Time / User</span><span>Tool</span><span>Server</span><span>Outcome</span><span>Duration</span></div>{audit.data.items.map((event) => <article key={event.id} className="grid gap-3 border-b border-zinc-800 px-5 py-4 last:border-0 lg:grid-cols-[180px_1fr_130px_120px_100px] lg:items-start"><div><time className="text-xs text-zinc-300">{dateTime.format(new Date(event.started_at))}</time><span className="mt-1 block truncate text-[11px] text-zinc-500">{actor.role === "admin" ? memberNames.get(event.user_id ?? "") ?? "Deleted user" : actor.email}</span></div><div><code className="text-xs text-zinc-200">{event.public_tool}</code><span className="mt-1 block text-[11px] uppercase tracking-wide text-zinc-600">{event.channel}</span>{event.error_summary ? <p className="mt-2 max-w-xl text-xs leading-5 text-red-300">{event.error_summary}</p> : null}</div><span className="text-xs text-zinc-400">{event.server_slug}</span><span className={`w-fit rounded-full border px-2 py-1 text-[11px] ${outcomeStyle[event.outcome]}`}>{event.outcome.replace("_", " ")}</span><span className="flex items-center gap-1.5 text-xs text-zinc-500"><Clock3 className="size-3.5" />{event.duration_ms} ms</span></article>)}</div>}
    {audit.data ? <footer className="mt-5 flex items-center justify-between text-xs text-zinc-500"><span>{audit.data.total === 0 ? "0" : `${offset + 1}–${Math.min(offset + PAGE_SIZE, audit.data.total)}`} of {audit.data.total}</span><div className="flex gap-2"><Button size="sm" disabled={offset === 0} onClick={() => setOffset((value) => Math.max(0, value - PAGE_SIZE))}><ChevronLeft className="size-4" />Previous</Button><Button size="sm" disabled={offset + PAGE_SIZE >= audit.data.total} onClick={() => setOffset((value) => value + PAGE_SIZE)}>Next<ChevronRight className="size-4" /></Button></div></footer> : null}
  </section>;
}
