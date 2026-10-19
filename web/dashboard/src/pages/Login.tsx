import { Braces, Eye, EyeOff, LockKeyhole, Network, Server, ShieldCheck } from "lucide-react";
import { useRef, useState, type FormEvent } from "react";
import { Button } from "../components/Button";
import { api } from "../lib/api";
import type { Actor } from "../lib/types";

export function Login({ onAuthenticated }: { onAuthenticated: (actor: Actor) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const emailRef = useRef<HTMLInputElement>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!email.trim() || !password) { setError("Enter your email and password."); emailRef.current?.focus(); return; }
    setBusy(true); setError("");
    try { onAuthenticated(await api.login(email, password)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Sign in failed."); }
    finally { setBusy(false); }
  }

  const inputClass = "mt-2 min-h-11 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20";
  return <main className="grid min-h-screen bg-[#09090B] text-zinc-50 lg:grid-cols-[minmax(0,1.15fr)_minmax(430px,.85fr)]">
    <section className="relative hidden overflow-hidden border-r border-zinc-800 px-[clamp(3rem,7vw,8rem)] py-16 lg:flex lg:flex-col lg:justify-between" aria-label="Platform overview">
      <div className="pointer-events-none absolute inset-0 opacity-35 [background-image:linear-gradient(#27272A_1px,transparent_1px),linear-gradient(90deg,#27272A_1px,transparent_1px)] [background-size:56px_56px] [mask-image:linear-gradient(to_bottom,black,transparent_78%)]" />
      <div className="relative flex items-center gap-3"><span className="grid size-9 place-items-center rounded-lg border border-indigo-400/30 bg-indigo-500/10 text-indigo-300"><Braces className="size-5" /></span><div><strong className="block text-sm">Kubernetes MCP Gateway</strong><span className="text-xs text-zinc-500">Team control plane</span></div></div>
      <div className="relative max-w-2xl py-20"><p className="mb-5 font-mono text-xs uppercase tracking-[.2em] text-indigo-400">One authenticated edge</p><h1 className="max-w-xl text-5xl font-semibold leading-[1.08] tracking-[-.04em] xl:text-6xl">Your tools, routed with intent.</h1><p className="mt-6 max-w-lg text-base leading-7 text-zinc-400">Register MCP servers, inspect discovered capabilities, and control access from a single Kubernetes-native gateway.</p>
        <div className="mt-12 grid max-w-xl grid-cols-3 overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950/70">
          {[{ icon: Server, value: "3+", label: "Upstreams" }, { icon: Network, value: "/mcp", label: "One endpoint" }, { icon: ShieldCheck, value: "RBAC", label: "Every call" }].map(({ icon: Icon, value, label }, index) => <div key={label} className={`p-4 ${index ? "border-l border-zinc-800" : ""}`}><Icon className="mb-6 size-4 text-zinc-500" /><strong className="block font-mono text-sm text-zinc-100">{value}</strong><span className="mt-1 block text-xs text-zinc-500">{label}</span></div>)}
        </div>
      </div>
      <p className="relative text-xs text-zinc-600">Streamable HTTP · Credential isolation · Dynamic discovery</p>
    </section>
    <section className="flex min-h-screen items-center justify-center px-6 py-12 sm:px-12">
      <form className="w-full max-w-sm" noValidate onSubmit={submit}>
        <div className="mb-10 lg:hidden"><span className="grid size-9 place-items-center rounded-lg border border-indigo-400/30 bg-indigo-500/10 text-indigo-300"><Braces className="size-5" /></span></div>
        <div className="mb-8"><p className="mb-2 text-xs font-medium uppercase tracking-[.16em] text-zinc-500">Operator access</p><h2 className="text-2xl font-semibold tracking-tight">Sign in to the gateway</h2><p className="mt-2 text-sm leading-6 text-zinc-400">Use your team account. Your session remains in a secure HTTP-only cookie.</p></div>
        {error ? <div className="mb-5 flex gap-3 rounded-md border border-red-900/60 bg-red-950/30 p-3 text-sm text-red-300" role="alert"><LockKeyhole className="mt-0.5 size-4 shrink-0" />{error}</div> : null}
        <label className="block text-sm font-medium text-zinc-300">Email address<input ref={emailRef} className={inputClass} type="email" autoComplete="username" placeholder="you@example.com" value={email} onChange={(event) => setEmail(event.target.value)} aria-invalid={!!error} /></label>
        <label className="mt-5 block text-sm font-medium text-zinc-300">Password<span className="relative block"><input className={`${inputClass} pr-11`} type={showPassword ? "text" : "password"} autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} aria-invalid={!!error} /><button className="absolute right-2 top-1/2 mt-1 grid size-8 -translate-y-1/2 place-items-center rounded-md text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500" type="button" onClick={() => setShowPassword((value) => !value)} aria-pressed={showPassword} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}</button></span></label>
        <Button type="submit" intent="primary" busy={busy} className="mt-7 w-full">Sign in</Button>
        <p className="mt-6 text-center text-xs text-zinc-600">Access is managed by your gateway administrator.</p>
      </form>
    </section>
  </main>;
}
