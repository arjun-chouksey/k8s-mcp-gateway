import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { LoaderCircle } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "../lib/utils";

export const buttonVariants = cva(
  "inline-flex min-h-9 items-center justify-center gap-2 rounded-md border px-3.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-[#09090B] disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      intent: {
        neutral: "border-zinc-700 bg-zinc-800 text-zinc-100 hover:bg-zinc-700",
        primary: "border-indigo-500 bg-indigo-500 text-white hover:bg-indigo-400",
        danger: "border-red-900/80 bg-red-950/60 text-red-300 hover:bg-red-950",
        ghost: "border-transparent bg-transparent text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100",
      },
      size: { default: "h-9", sm: "h-8 px-2.5 text-xs", icon: "size-9 p-0" },
    },
    defaultVariants: { intent: "neutral", size: "default" },
  },
);

interface Props extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  busy?: boolean;
}

export function Button({ asChild, intent, size, busy = false, children, className, disabled, ...props }: Props) {
  if (asChild) return <Slot className={cn(buttonVariants({ intent, size }), className)} {...props}>{children}</Slot>;
  const Component = "button";
  return (
    <Component className={cn(buttonVariants({ intent, size }), className)} disabled={disabled || busy} aria-busy={busy} {...props}>
      {busy ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : null}
      {children}
    </Component>
  );
}
