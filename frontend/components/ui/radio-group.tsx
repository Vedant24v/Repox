"use client"

import { Radio as RadioPrimitive } from "@base-ui/react/radio"
import { RadioGroup as RadioGroupPrimitive } from "@base-ui/react/radio-group"

import { cn } from "@/lib/utils"

function RadioGroup({ className, ...props }: RadioGroupPrimitive.Props) {
  return (
    <RadioGroupPrimitive
      data-slot="radio-group"
      className={cn("grid w-full gap-3", className)}
      {...props}
    />
  )
}

function RadioGroupItem({ className, ...props }: RadioPrimitive.Root.Props) {
  return (
    <RadioPrimitive.Root
      data-slot="radio-group-item"
      className={cn(
        "group/radio-group-item peer relative flex aspect-square size-6 shrink-0 rounded-full border-0 bg-[#EFEBF5] shadow-clay-pressed outline-none transition-all duration-200 cursor-pointer hover:scale-105 active:scale-95 focus-visible:ring-4 focus-visible:ring-clay-primary/20 disabled:cursor-not-allowed disabled:opacity-50 data-checked:bg-gradient-to-br data-checked:from-[#A78BFA] data-checked:to-[#7C3AED] data-checked:shadow-clay-button",
        className
      )}
      {...props}
    >
      <RadioPrimitive.Indicator
        data-slot="radio-group-indicator"
        className="flex size-full items-center justify-center"
      >
        <span className="size-2 rounded-full bg-white shadow-[0_1px_2px_rgba(0,0,0,0.2)]" />
      </RadioPrimitive.Indicator>
    </RadioPrimitive.Root>
  )
}

export { RadioGroup, RadioGroupItem }
