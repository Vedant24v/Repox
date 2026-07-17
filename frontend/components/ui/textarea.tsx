import * as React from "react"

import { cn } from "@/lib/utils"

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "flex field-sizing-content min-h-24 w-full rounded-2xl border-0 bg-[#EFEBF5] px-6 py-4 text-base text-clay-foreground shadow-clay-pressed transition-all duration-200 outline-none placeholder:text-clay-muted/60 focus:bg-white focus:ring-4 focus:ring-clay-primary/20 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20",
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
