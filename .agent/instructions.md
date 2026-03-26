# Textbook RAG — Frontend Conventions

## Shared Layout: `SidebarLayout`

**Every module page** (Dashboard sub-pages, Library, Chat BookPicker, etc.) MUST use the shared `SidebarLayout` component:

```
import { SidebarLayout, type SidebarItem, type ViewMode } from '@/features/shared/components/SidebarLayout'
```

### Required Pattern

```tsx
<SidebarLayout
  title="模块名称"
  icon={<SomeIcon />}
  sidebarItems={sidebarItems}       // SidebarItem[] — supports category → subcategory hierarchy via `indent`
  activeFilter={filter}
  onFilterChange={setFilter}
  showViewToggle                    // Enable card/list toggle
  viewMode={viewMode}
  onViewModeChange={setViewMode}
  sidebarFooter={<p>...</p>}        // Optional stats
  toolbar={<button>...</button>}    // Optional action buttons
  footer={<div>...</div>}           // Optional bottom action bar (e.g. BookPicker "Start Chat")
  loading={loading}
  error={error}
  onRetry={retry}
>
  {viewMode === 'cards' ? <CardGrid /> : <TableView />}
</SidebarLayout>
```

### Key Rules

1. **Never hand-roll a sidebar** — always use `SidebarLayout`
2. **Always support card + list views** via `showViewToggle` + `viewMode`
3. **Subcategories** use `indent: true` in `SidebarItem`
4. **Hierarchical filter keys** use `category::subcategory` format (e.g. `textbook::Python`)
5. **File location**: `src/features/shared/components/SidebarLayout.tsx`

### Existing Pages Using This Pattern

| Page | File |
|------|------|
| Models | `dashboard/models/page.tsx` |
| Prompts | `dashboard/prompts/page.tsx` |
| Queries | `dashboard/queries/page.tsx` |
| BookPicker | `features/chat/book/BookPicker.tsx` |

## Styling

- Use **semantic Tailwind tokens** (`text-foreground`, `bg-card`, `border-border`) — never hardcode colors
- Supports both light and dark mode via `next-themes` with `attribute="class"`
- Use `cn()` utility from `@/features/shared/utils` for conditional classes

## Books Collection

- Books have `category` (select: textbook/ecdev/real_estate) and `subcategory` (free text)
- `BookSummary` type includes both fields
- `fetchBooks()` returns category + subcategory from Payload CMS
