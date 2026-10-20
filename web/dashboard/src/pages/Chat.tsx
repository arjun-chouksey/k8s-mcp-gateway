import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, CornerDownLeft, MessageSquarePlus, Octagon, PanelLeftClose, Wrench } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import { Button } from "../components/Button";
import { ToolCallCard } from "../components/ToolCallCard";
import { api } from "../lib/api";
import { type ChatEvent, streamChat } from "../lib/chat";
import type { ToolTrace } from "../lib/types";
import { cn } from "../lib/utils";

type LiveTurn = { prompt: string; answer: string; traces: ToolTrace[]; error: string | null; conversationId: string | null };
const emptyTurn: LiveTurn = { prompt: "", answer: "", traces: [], error: null, conversationId: null };

function timeLabel(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

export function Chat() {
  const cache = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [live, setLive] = useState<LiveTurn>(emptyTurn);
  const [streaming, setStreaming] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const conversations = useQuery({ queryKey: ["conversations"], queryFn: api.conversations });
  const detail = useQuery({ queryKey: ["conversation", activeId], queryFn: () => api.conversation(activeId!), enabled: Boolean(activeId) });

  useEffect(() => { if (typeof endRef.current?.scrollIntoView === "function") endRef.current.scrollIntoView({ block: "end" }); }, [live, detail.data]);
  useEffect(() => () => abortRef.current?.abort(), []);

  function newConversation() {
    if (streaming) return;
    setActiveId(null); setLive(emptyTurn); setPrompt(""); setHistoryOpen(false);
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    const text = prompt.trim();
    if (!text || streaming) return;
    const controller = new AbortController(); abortRef.current = controller;
    let resolvedConversationId = activeId;
    let streamFailed = false;
    setPrompt(""); setStreaming(true); setLive({ ...emptyTurn, prompt: text, conversationId: activeId });
    try {
      await streamChat(text, activeId, (item: ChatEvent) => {
        resolvedConversationId = item.conversation_id;
        setLive((current) => {
          const base = { ...current, conversationId: item.conversation_id };
          if (item.type === "tool_call") return { ...base, traces: [...base.traces, { call_id: item.call_id, name: item.name, outcome: "running" }] };
          if (item.type === "tool_result") return { ...base, traces: base.traces.map((trace) => trace.call_id === item.call_id ? { call_id: item.call_id, name: item.name, outcome: item.outcome, duration_ms: item.duration_ms } : trace) };
          if (item.type === "text_delta") return { ...base, answer: base.answer + item.text };
          if (item.type === "error") { streamFailed = true; return { ...base, error: item.message }; }
          return base;
        });
      }, controller.signal);
      const id = resolvedConversationId;
      await cache.invalidateQueries({ queryKey: ["conversations"] });
      if (id) {
        setActiveId(id);
        await cache.invalidateQueries({ queryKey: ["conversation", id] });
        if (!streamFailed) {
          await cache.fetchQuery({ queryKey: ["conversation", id], queryFn: () => api.conversation(id) });
          setLive(emptyTurn);
        }
      }
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) setLive((current) => ({ ...current, error: error instanceof Error ? error.message : "Chat failed" }));
    } finally { setStreaming(false); abortRef.current = null; }
  }

  const messages = detail.data?.messages ?? [];
  return <section className="flex h-[calc(100vh-4rem)] min-h-[620px] overflow-hidden md:h-screen">
    <aside className={cn("absolute inset-y-16 left-0 z-20 w-[min(82vw,300px)] border-r border-zinc-800 bg-[#0C0C0E] p-3 transition-transform md:static md:inset-auto md:block md:w-72 md:translate-x-0", historyOpen ? "translate-x-0" : "-translate-x-full")} aria-label="Conversation history">
      <Button className="w-full justify-start" onClick={newConversation} disabled={streaming}><MessageSquarePlus className="size-4" />New conversation</Button>
      <div className="mt-5 flex items-center justify-between px-1"><h2 className="text-[10px] font-semibold uppercase tracking-[.18em] text-zinc-500">Recent conversations</h2><span className="font-mono text-[10px] text-zinc-600">{conversations.data?.length ?? 0}</span></div>
      <div className="mt-2 space-y-1 overflow-y-auto pb-8 md:max-h-[calc(100vh-110px)]">
        {conversations.isPending ? <p className="px-2 py-5 text-xs text-zinc-500" role="status">Loading history…</p> : null}
        {conversations.data?.length === 0 ? <p className="px-2 py-5 text-xs leading-5 text-zinc-500">Your tool-backed conversations will appear here.</p> : null}
        {conversations.data?.map((item) => <button key={item.id} className={cn("w-full border-l-2 px-3 py-2.5 text-left transition", activeId === item.id ? "border-indigo-400 bg-zinc-900" : "border-transparent hover:bg-zinc-900/70")} onClick={() => { if (!streaming) { setActiveId(item.id); setLive(emptyTurn); setHistoryOpen(false); } }}>
          <span className="block truncate text-sm text-zinc-200">{item.title}</span><span className="mt-1 block text-[10px] text-zinc-600">{timeLabel(item.updated_at)}</span>
        </button>)}
      </div>
    </aside>

    <div className="flex min-w-0 flex-1 flex-col bg-[#09090B]">
      <header className="flex h-16 shrink-0 items-center gap-3 border-b border-zinc-800 px-4 md:px-7">
        <Button intent="ghost" size="icon" className="md:hidden" aria-label="Open conversation history" onClick={() => setHistoryOpen((value) => !value)}><PanelLeftClose className="size-4" /></Button>
        <div><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-indigo-300">Gateway agent</p><h1 className="text-sm font-semibold text-zinc-100">{detail.data?.title || "New conversation"}</h1></div>
        <span className="ml-auto hidden items-center gap-2 text-[11px] text-zinc-500 sm:flex"><span className="size-1.5 rounded-full bg-emerald-400" />Tools run through /mcp</span>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8" aria-live="polite">
        <div className="mx-auto max-w-3xl space-y-6">
          {!activeId && !live.prompt ? <div className="grid min-h-[48vh] place-content-center text-center"><span className="mx-auto grid size-12 place-items-center border border-zinc-700 bg-zinc-900"><Bot className="size-5 text-indigo-300" /></span><h2 className="mt-5 text-xl font-semibold tracking-tight">Operate the store through one gateway</h2><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-zinc-500">Ask for products, orders, policy, or currency work. Each real MCP call appears in the transcript.</p></div> : null}
          {detail.isPending && activeId ? <p role="status" className="py-10 text-center text-sm text-zinc-500">Loading conversation…</p> : null}
          {messages.map((message) => <div key={message.id} className={cn("max-w-[88%]", message.role === "user" ? "ml-auto" : "mr-auto")}>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[.16em] text-zinc-600">{message.role === "user" ? "You" : "Agent"}</p>
            {message.tool_calls?.length ? <div className="mb-3 space-y-2">{message.tool_calls.map((trace) => <ToolCallCard key={trace.call_id} trace={trace} />)}</div> : null}
            <div className={cn("whitespace-pre-wrap text-sm leading-6", message.role === "user" ? "border border-zinc-700 bg-zinc-800 px-4 py-3 text-zinc-100" : "text-zinc-300")}>{message.text}</div>
          </div>)}
          {live.prompt ? <div className="ml-auto max-w-[88%]"><p className="mb-2 text-[10px] font-semibold uppercase tracking-[.16em] text-zinc-600">You</p><div className="border border-zinc-700 bg-zinc-800 px-4 py-3 text-sm leading-6 text-zinc-100">{live.prompt}</div></div> : null}
          {live.traces.length || live.answer || live.error ? <div className="mr-auto max-w-[92%]"><p className="mb-2 text-[10px] font-semibold uppercase tracking-[.16em] text-zinc-600">Agent</p><div className="mb-3 space-y-2">{live.traces.map((trace) => <ToolCallCard key={trace.call_id} trace={trace} />)}</div>{live.answer ? <div className="whitespace-pre-wrap text-sm leading-6 text-zinc-300">{live.answer}</div> : null}{live.error ? <div role="alert" className="border-l-2 border-rose-500 bg-rose-950/20 px-3 py-2 text-sm text-rose-200">{live.error}</div> : null}</div> : null}
          <div ref={endRef} />
        </div>
      </div>

      <form noValidate onSubmit={(event) => void send(event)} className="shrink-0 border-t border-zinc-800 bg-[#0C0C0E] px-4 py-4 md:px-8">
        <div className="mx-auto flex max-w-3xl items-end gap-2 border border-zinc-700 bg-zinc-900 p-2 focus-within:border-indigo-400">
          <label className="sr-only" htmlFor="chat-prompt">Message</label><textarea id="chat-prompt" rows={2} value={prompt} disabled={streaming} onChange={(event) => setPrompt(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="Ask the gateway to use a tool…" className="max-h-40 min-h-12 flex-1 resize-none bg-transparent px-2 py-2 text-sm text-zinc-100 outline-none placeholder:text-zinc-600" />
          {streaming ? <Button type="button" intent="neutral" size="sm" onClick={() => abortRef.current?.abort()}><Octagon className="size-4" />Stop</Button> : <Button type="submit" size="sm" disabled={!prompt.trim()}><CornerDownLeft className="size-4" />Send</Button>}
        </div>
        <p className="mx-auto mt-2 flex max-w-3xl items-center gap-1.5 text-[10px] text-zinc-600"><Wrench className="size-3" />Tool outputs are redacted before they reach this screen.</p>
      </form>
    </div>
  </section>;
}
