import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../lib/utils";

interface Props {
  open: boolean;
  title: string;
  description?: string;
  children: ReactNode;
  onClose: () => void;
  destructive?: boolean;
}

export function Dialog({ open, title, description, children, onClose, destructive = false }: Props) {
  return <DialogPrimitive.Root open={open} onOpenChange={(next) => { if (!next) onClose(); }}>
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-black/70 backdrop-blur-[2px]" />
      <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 max-h-[calc(100vh-2rem)] w-[calc(100vw-2rem)] max-w-xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-zinc-800 bg-[#18181B] text-zinc-50 shadow-2xl focus:outline-none">
        <header className={cn("border-b border-zinc-800 px-6 py-5", destructive && "bg-red-950/20")}>
          <DialogPrimitive.Title className="text-lg font-semibold tracking-tight">{title}</DialogPrimitive.Title>
          {description ? <DialogPrimitive.Description className="mt-1.5 text-sm leading-6 text-zinc-400">{description}</DialogPrimitive.Description> : null}
        </header>
        {children}
        <DialogPrimitive.Close className="absolute right-4 top-4 rounded-md p-1.5 text-zinc-500 transition hover:bg-zinc-800 hover:text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500" aria-label="Close dialog"><X className="size-4" /></DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  </DialogPrimitive.Root>;
}
