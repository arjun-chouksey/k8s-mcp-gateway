import { Eye, EyeOff, Info } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import type { AuthType, ServerCreate, ServerRecord, ServerUpdate } from "../lib/types";
import { Button } from "./Button";
import { Dialog } from "./Dialog";

interface Props { open: boolean; server: ServerRecord | null; busy: boolean; error: string | null; onClose: () => void; onCreate: (payload: ServerCreate) => Promise<void>; onUpdate: (payload: ServerUpdate) => Promise<void>; }

const inputClass = "mt-2 min-h-10 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 disabled:cursor-not-allowed disabled:bg-zinc-900 disabled:text-zinc-500";

export function ServerForm({ open, server, busy, error, onClose, onCreate, onUpdate }: Props) {
  const [name, setName] = useState(""); const [slug, setSlug] = useState(""); const [url, setUrl] = useState("");
  const [authType, setAuthType] = useState<AuthType>("none"); const [header, setHeader] = useState(""); const [credential, setCredential] = useState("");
  const [replaceCredential, setReplaceCredential] = useState(false); const [showCredential, setShowCredential] = useState(false); const [fieldError, setFieldError] = useState("");
  const firstField = useRef<HTMLInputElement>(null);
  useEffect(() => { if (!open) return; setName(server?.display_name ?? ""); setSlug(server?.slug ?? ""); setUrl(server?.url ?? ""); setAuthType(server?.auth_type ?? "none"); setHeader(server?.auth_header ?? ""); setCredential(""); setReplaceCredential(false); setShowCredential(false); setFieldError(""); }, [open, server]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim() || !slug.trim() || !url.trim()) { setFieldError("Name, slug, and endpoint URL are required."); firstField.current?.focus(); return; }
    const usesCredential = authType !== "none";
    if (!server && usesCredential && !credential) { setFieldError("A credential is required for authenticated servers."); return; }
    setFieldError("");
    if (!server) { await onCreate({ slug: slug.trim(), display_name: name.trim(), url: url.trim(), auth_type: authType, auth_header: authType === "header" ? header.trim() : null, credential: usesCredential ? credential : null, enabled: true, connect_timeout_ms: 3000, call_timeout_ms: 20000 }); return; }
    await onUpdate({ display_name: name.trim(), url: url.trim(), auth_type: authType, auth_header: authType === "header" ? header.trim() : null, credential_action: replaceCredential && usesCredential ? "set" : authType === "none" ? "clear" : "keep", ...(replaceCredential && usesCredential ? { credential } : {}) });
  }
  const credentialEnabled = authType !== "none" && (!server || replaceCredential);
  return <Dialog open={open} title={server ? `Edit ${server.display_name}` : "Register MCP server"} description={server ? "Update connectivity settings. Existing credentials remain unchanged unless replaced." : "Add a Streamable HTTP upstream to the gateway registry."} onClose={onClose}>
    <form className="space-y-5 p-6" noValidate onSubmit={submit}>
      {(fieldError || error) ? <div className="rounded-md border border-red-900/60 bg-red-950/30 p-3 text-sm text-red-300" role="alert">{fieldError || error}</div> : null}
      <label className="block text-sm font-medium text-zinc-300">Display name<input ref={firstField} autoFocus className={inputClass} value={name} onChange={(event) => setName(event.target.value)} aria-invalid={!!fieldError && !name.trim()} /></label>
      <label className="block text-sm font-medium text-zinc-300">Stable slug<input className={inputClass} value={slug} onChange={(event) => setSlug(event.target.value)} disabled={!!server} pattern="[a-z][a-z0-9-]*" aria-describedby="slug-help" /><small id="slug-help" className="mt-1.5 block text-xs leading-5 text-zinc-500">Lowercase letters, numbers, and hyphens. This becomes the permanent tool prefix.</small></label>
      <label className="block text-sm font-medium text-zinc-300">Streamable HTTP endpoint<input className={inputClass} type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://server.example.com/mcp" /></label>
      <label className="block text-sm font-medium text-zinc-300">Authentication<select className={inputClass} value={authType} onChange={(event) => setAuthType(event.target.value as AuthType)}><option value="none">No credential</option><option value="bearer">Bearer token</option><option value="header">Custom header</option></select></label>
      {authType === "header" ? <label className="block text-sm font-medium text-zinc-300">Header name<input className={inputClass} value={header} onChange={(event) => setHeader(event.target.value)} placeholder="X-API-Key" /></label> : null}
      {server && authType !== "none" ? <label className="flex cursor-pointer items-center gap-3 rounded-md border border-zinc-800 bg-zinc-950/50 p-3 text-sm text-zinc-300"><input className="size-4 accent-indigo-500" type="checkbox" checked={replaceCredential} onChange={(event) => setReplaceCredential(event.target.checked)} />Replace the stored credential</label> : null}
      {credentialEnabled ? <label className="block text-sm font-medium text-zinc-300">Credential<span className="relative block"><input className={`${inputClass} pr-11`} type={showCredential ? "text" : "password"} autoComplete="new-password" value={credential} onChange={(event) => setCredential(event.target.value)} /><button className="absolute right-2 top-1/2 mt-1 grid size-8 -translate-y-1/2 place-items-center rounded-md text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200" type="button" onClick={() => setShowCredential((value) => !value)} aria-pressed={showCredential} aria-label={showCredential ? "Hide credential" : "Show credential"}>{showCredential ? <EyeOff className="size-4" /> : <Eye className="size-4" />}</button></span><small className="mt-2 flex items-center gap-1.5 text-xs text-zinc-500"><Info className="size-3.5" />Write-only. The gateway never returns this value.</small></label> : null}
      <div className="flex justify-end gap-2 border-t border-zinc-800 pt-5"><Button type="button" intent="ghost" onClick={onClose}>Cancel</Button><Button type="submit" intent="primary" busy={busy}>{server ? "Save changes" : "Register server"}</Button></div>
    </form>
  </Dialog>;
}
