import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from "@tanstack/react-query";
import { Braces, ChevronLeft, KeyRound, LayoutDashboard, LogOut, MessageSquare, ScrollText, Server, Settings, ShieldCheck, Users } from "lucide-react";
import { useState } from "react";
import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import { Button } from "./components/Button";
import { ToastRegion, type Notice } from "./components/Toast";
import { api } from "./lib/api";
import { cn } from "./lib/utils";
import type { Actor } from "./lib/types";
import { Login } from "./pages/Login";
import { InviteAccept } from "./pages/InviteAccept";
import { MyKeys } from "./pages/MyKeys";
import { Servers } from "./pages/Servers";
import { Team } from "./pages/Team";

const futureNavigation = [
  { label: "AI Chat", icon: MessageSquare },
  { label: "Audit Logs", icon: ScrollText },
  { label: "Settings", icon: Settings },
];

function Mark({ compact = false }: { compact?: boolean }) {
  return <div className="flex min-w-0 items-center gap-3"><span className="grid size-8 shrink-0 place-items-center rounded-lg border border-indigo-400/30 bg-indigo-500/10 text-indigo-300"><Braces className="size-4" /></span>{compact ? null : <div className="min-w-0"><strong className="block truncate text-sm font-semibold text-zinc-100">Kubernetes MCP</strong><span className="block text-[11px] text-zinc-500">Gateway console</span></div>}</div>;
}

function Shell({ actor }: { actor: Actor }) {
  const [collapsed, setCollapsed] = useState(false);
  const [notices, setNotices] = useState<Notice[]>([]);
  const cache = useQueryClient();
  function notify(tone: Notice["tone"], message: string) {
    const id = Date.now();
    setNotices((current) => [...current.slice(-2), { id, tone, message }]);
    window.setTimeout(() => setNotices((current) => current.filter((item) => item.id !== id)), 4500);
  }
  async function logout() {
    try { await api.logout(); } finally { cache.setQueryData(["session"], null); }
  }
  return <div className={cn("min-h-screen bg-[#09090B] text-zinc-50 md:grid", collapsed ? "md:grid-cols-[72px_minmax(0,1fr)]" : "md:grid-cols-[240px_minmax(0,1fr)]")}>
    <aside className="sticky top-0 z-30 flex h-16 items-center border-b border-zinc-800 bg-[#0C0C0E] px-4 md:h-screen md:flex-col md:items-stretch md:border-b-0 md:border-r md:px-3 md:py-4">
      <div className="flex items-center justify-between"><Mark compact={collapsed} /><Button intent="ghost" size="icon" className="hidden md:inline-flex" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} onClick={() => setCollapsed((value) => !value)}><ChevronLeft className={cn("size-4 transition-transform", collapsed && "rotate-180")} /></Button></div>
      <nav className="ml-auto flex items-center gap-1 md:ml-0 md:mt-8 md:grid" aria-label="Primary navigation">
        <span className={cn("hidden px-3 pb-2 text-[10px] font-semibold uppercase tracking-[.18em] text-zinc-600 md:block", collapsed && "sr-only")}>Workspace</span>
        <span className="hidden items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-600 md:flex" title="Overview is available in a later iteration"><LayoutDashboard className="size-4" /><span className={cn(collapsed && "hidden")}>Overview</span></span>
        <NavLink to="/servers" className={({ isActive }) => cn("flex items-center gap-3 rounded-md px-3 py-2 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500", isActive ? "bg-zinc-800 text-zinc-50" : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200")}><Server className="size-4" /><span className={cn("hidden md:block", collapsed && "md:hidden")}>MCP Servers</span></NavLink>
        {actor.role === "admin" ? <NavLink to="/team" aria-label="Team" className={({ isActive }) => cn("flex items-center gap-3 rounded-md px-3 py-2 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500", isActive ? "bg-zinc-800 text-zinc-50" : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200")}><Users className="size-4" /><span className={cn("hidden md:block", collapsed && "md:hidden")}>Team</span></NavLink> : null}
        <NavLink to="/keys" aria-label="API Keys" className={({ isActive }) => cn("flex items-center gap-3 rounded-md px-3 py-2 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500", isActive ? "bg-zinc-800 text-zinc-50" : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200")}><KeyRound className="size-4" /><span className={cn("hidden md:block", collapsed && "md:hidden")}>API Keys</span></NavLink>
        {futureNavigation.map(({ label, icon: Icon }) => <span key={label} className="hidden items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-600 md:flex" title={`${label} is not part of T-023`}><Icon className="size-4" /><span className={cn(collapsed && "hidden")}>{label}</span></span>)}
      </nav>
      <div className="ml-3 hidden border-t border-zinc-800 pt-4 md:ml-0 md:mt-auto md:block">
        <div className={cn("mb-3 flex items-center gap-3 px-2", collapsed && "justify-center px-0")}><span className="grid size-8 shrink-0 place-items-center rounded-full bg-zinc-800 text-xs font-semibold text-zinc-200">{actor.email.slice(0, 1).toUpperCase()}</span><div className={cn("min-w-0", collapsed && "hidden")}><strong className="block truncate text-xs font-medium text-zinc-200">{actor.email}</strong><span className="inline-flex items-center gap-1 text-[11px] capitalize text-zinc-500"><ShieldCheck className="size-3" />{actor.role}</span></div></div>
        <Button intent="ghost" size={collapsed ? "icon" : "sm"} className={cn(!collapsed && "w-full justify-start")} onClick={() => void logout()} aria-label="Sign out"><LogOut className="size-4" />{collapsed ? null : "Sign out"}</Button>
      </div>
    </aside>
    <main className="min-w-0"><Routes><Route path="/servers" element={<Servers actor={actor} notify={notify} onSessionExpired={() => cache.setQueryData(["session"], null)} />} /><Route path="/team" element={actor.role === "admin" ? <Team notify={notify} /> : <Navigate to="/servers" replace />} /><Route path="/keys" element={<MyKeys notify={notify} />} /><Route path="/" element={<Navigate to="/servers" replace />} /><Route path="/login" element={<Navigate to="/servers" replace />} /><Route path="*" element={<section className="grid min-h-[70vh] place-content-center text-center"><p className="text-sm font-medium text-zinc-500">404</p><h1 className="mt-2 text-2xl font-semibold">Page not found</h1><Button asChild className="mt-5"><NavLink to="/servers">Return to servers</NavLink></Button></section>} /></Routes></main>
    <ToastRegion notices={notices} />
  </div>;
}

function SessionBoundary() {
  const cache = useQueryClient();
  const session = useQuery({ queryKey: ["session"], queryFn: api.me });
  if (session.isPending) return <main className="grid min-h-screen place-content-center gap-3 bg-[#09090B] text-center text-sm text-zinc-400" role="status"><span className="mx-auto size-5 animate-spin rounded-full border-2 border-zinc-700 border-t-indigo-400" />Checking session…</main>;
  if (!session.data) return <Login onAuthenticated={(actor) => cache.setQueryData(["session"], actor)} />;
  return <Shell actor={session.data} />;
}

export default function App() {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } }));
  return <QueryClientProvider client={client}><BrowserRouter><Routes><Route path="/invite" element={<InviteAccept />} /><Route path="*" element={<SessionBoundary />} /></Routes></BrowserRouter></QueryClientProvider>;
}
