import { AlertTriangle, Check } from "lucide-react";

export interface Notice { id: number; tone: "success" | "error"; message: string }

export function ToastRegion({ notices }: { notices: Notice[] }) {
  return (
    <div className="fixed bottom-5 right-5 z-[60] grid w-[min(380px,calc(100vw-2rem))] gap-2" aria-live="polite" aria-atomic="true">
      {notices.map((notice) => (
        <div className={`flex items-center gap-3 rounded-lg border bg-zinc-900 px-4 py-3 text-sm shadow-2xl ${notice.tone === "success" ? "border-emerald-900/70 text-emerald-200" : "border-red-900/70 text-red-200"}`} key={notice.id} role="status">
          {notice.tone === "success" ? <Check className="size-4 shrink-0" /> : <AlertTriangle className="size-4 shrink-0" />}
          {notice.message}
        </div>
      ))}
    </div>
  );
}
