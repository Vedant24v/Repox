import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-[20px] font-heading font-bold tracking-wide transition-all duration-200 outline-none select-none active:scale-[0.92] active:shadow-clay-pressed disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-gradient-to-br from-[#A78BFA] to-[#7C3AED] text-white shadow-clay-button hover:shadow-clay-button-hover hover:-translate-y-1 active:translate-y-0",
        outline:
          "border-2 border-clay-primary/20 bg-transparent text-clay-primary hover:border-clay-primary hover:bg-clay-primary/5 shadow-clay-button hover:shadow-clay-button-hover hover:-translate-y-1 active:translate-y-0",
        secondary:
          "bg-white text-clay-foreground shadow-clay-button hover:shadow-clay-button-hover hover:-translate-y-1 active:translate-y-0",
        ghost:
          "text-clay-foreground hover:bg-clay-primary/10 hover:text-clay-primary active:bg-clay-primary/25",
        destructive:
          "bg-red-500 text-white shadow-clay-button hover:shadow-clay-button-hover hover:-translate-y-1 active:translate-y-0",
        link: "text-clay-primary underline-offset-4 hover:underline",
      },
      size: {
        default:
          "h-14 gap-2 px-6 text-base",
        xs: "h-9 gap-1 rounded-xl px-3 text-xs",
        sm: "h-11 gap-1.5 rounded-2xl px-4 text-sm",
        lg: "h-16 gap-2.5 px-8 text-lg",
        icon: "size-14 rounded-2xl",
        "icon-xs":
          "size-9 rounded-xl",
        "icon-sm":
          "size-11 rounded-2xl",
        "icon-lg": "size-16 rounded-[20px]",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
