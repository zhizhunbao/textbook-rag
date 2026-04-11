/**
 * UIComponents - Barrel export for all shared UI components
 *
 * @module shared/components/ui
 * @template none
 * @reference none
 */

// shadcn/ui 基础组件
export { Button, buttonVariants } from './button'
export { Input } from './input'
export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent } from './card'
export { Alert, AlertTitle, AlertDescription } from './alert'
export { Label } from './label'
export { Textarea } from './textarea'

// shadcn/ui 增强组件
export {
  Dialog,
  DialogPortal,
  DialogOverlay,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from './dialog'

export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuCheckboxItem,
  DropdownMenuRadioItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuGroup,
  DropdownMenuPortal,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuRadioGroup,
} from './dropdown-menu'

export { Avatar, AvatarImage, AvatarFallback } from './avatar'
export { Badge, badgeVariants } from './badge'
export { Separator } from './separator'
export { Skeleton } from './skeleton'
export { Toaster } from './sonner'
export { Tabs, TabsList, TabsTrigger, TabsContent } from './tabs'
export { ScrollArea, ScrollBar } from './scroll-area'
export { Progress } from './progress'
export { Switch } from './switch'
export {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from './tooltip'

// Sheet 组件
export {
  Sheet,
  SheetPortal,
  SheetOverlay,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
} from './sheet'

// Form components (react-hook-form + zod integration)
export {
  useFormField,
  Form,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
  FormField,
} from './form'

// Popover
export { Popover, PopoverTrigger, PopoverContent, PopoverAnchor } from './popover'

// Command (cmdk)
export {
  Command,
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
  CommandSeparator,
} from './command'

// Business components
export { ErrorBoundary } from './error-boundary'
