import { Check, Copy, KeyRound, ShieldAlert } from "lucide-react";
import { useState } from "react";
import type { IssuedKey } from "../lib/types";
import { Button } from "./Button";
import { Dialog } from "./Dialog";

export function KeyOnceModal({ issued, onClose, onRevoke }: { issued: IssuedKey | null; onClose: () => void; onRevoke?: () => Promise<void> }) {
  const [copied, setCopied] = useState("");
  if (!issued) return null;
  const gatewayUrl = `${window.location.origin}/mcp`;
  const cursor = JSON.stringify({ mcpServers: { "kubernetes-gateway": { url: gatewayUrl, headers: { Authorization: `Bearer ${issued.key}` } } } }, null, 2);
  const inspector = `Transport: Streamable HTTP\nURL: ${gatewayUrl}\nAuthorization: Bearer ${issued.key}`;
  async function copy(label: string, value: string) { await navigator.clipboard.writeText(value); setCopied(label); window.setTimeout(() => setCopied(""), 1800); }
  return <Dialog open title="API key created" description="This secret is shown once. Copy it before closing this window." onClose={onClose}>
    <div className="space-y-5 p-6">
      <div className="flex gap-3 rounded-md border border-amber-900/60 bg-amber-950/25 p-3 text-sm leading-6 text-amber-200"><ShieldAlert className="mt-1 size-4 shrink-0" /><span>The gateway stores only a keyed digest. This value cannot be recovered later.</span></div>
      <CopyBlock label="Plaintext key" value={issued.key} copied={copied === "key"} onCopy={() => void copy("key", issued.key)} />
      <div className="grid gap-3 lg:grid-cols-2"><CopyBlock label="MCP Inspector" value={inspector} copied={copied === "inspector"} onCopy={() => void copy("inspector", inspector)} /><CopyBlock label="Cursor / Claude Code config" value={cursor} copied={copied === "config"} onCopy={() => void copy("config", cursor)} /></div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-zinc-800 pt-5"><p className="flex items-center gap-2 text-xs text-zinc-500"><KeyRound className="size-3.5" />Prefix retained: <code>{issued.prefix}</code></p><div className="flex gap-2">{onRevoke ? <Button intent="danger" onClick={() => void onRevoke()}>Revoke now</Button> : null}<Button intent="primary" onClick={onClose}>I saved the key</Button></div></div>
    </div>
  </Dialog>;
}

function CopyBlock({ label, value, copied, onCopy }: { label: string; value: string; copied: boolean; onCopy: () => void }) {
  return <div className="rounded-md border border-zinc-800 bg-zinc-950"><div className="flex items-center justify-between border-b border-zinc-800 px-3 py-2"><span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">{label}</span><Button size="sm" intent="ghost" onClick={onCopy}>{copied ? <Check className="size-3.5 text-emerald-400" /> : <Copy className="size-3.5" />}{copied ? "Copied" : "Copy"}</Button></div><pre className="max-h-44 overflow-auto whitespace-pre-wrap break-all p-3 text-[11px] leading-5 text-zinc-300">{value}</pre></div>;
}
