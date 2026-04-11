/**
 * Skeleton - Loading placeholder with pulse animation
 *
 * @module shared/components/ui
 * @template none
 * @reference shadcn-ui/ui/skeleton
 */
import { cn } from "@/features/shared/utils"

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-primary/10", className)}
      {...props}
    />
  )
}

export { Skeleton }
