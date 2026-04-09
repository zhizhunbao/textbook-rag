/**
 * shared/books/CategoryIcons.tsx — dynamic category icon resolver.
 *
 * Provides a function that returns icon ReactNodes for any category,
 * including dynamically-created categories (e.g. 'professional_profile').
 *
 * Replaces per-component hardcoded CATEGORY_ICONS maps.
 */

'use client'

import type { ReactNode } from 'react'
import { BookOpen, Building2, Home, FolderOpen } from 'lucide-react'
import { cn } from '@/features/shared/utils'

// ============================================================
// Known category icons
// ============================================================

const KNOWN_ICONS: Record<string, { Icon: typeof BookOpen; color: string }> = {
  textbook:    { Icon: BookOpen,  color: 'text-blue-400' },
  ecdev:       { Icon: Building2, color: 'text-emerald-400' },
  real_estate: { Icon: Home,      color: 'text-amber-400' },
}

// ============================================================
// Public API
// ============================================================

/**
 * Get icon ReactNode for a category key.
 *
 * Known categories get their specific icon + color.
 * Unknown/dynamic categories get a FolderOpen icon with violet color.
 */
export function getCategoryIcon(category: string, className = 'h-4 w-4 shrink-0'): ReactNode {
  const known = KNOWN_ICONS[category]
  if (known) {
    const { Icon, color } = known
    return <Icon className={cn(className, color)} />
  }
  // Dynamic fallback for LLM-classified categories
  return <FolderOpen className={cn(className, 'text-violet-400')} />
}

/**
 * Build a Record<string, ReactNode> of category icons from actual book data.
 *
 * This replaces per-component hardcoded CATEGORY_ICONS maps.
 * It includes entries for ALL categories present in the data,
 * not just the known ones.
 */
export function buildCategoryIcons(
  categories: string[],
  className = 'h-4 w-4 shrink-0',
): Record<string, ReactNode> {
  const icons: Record<string, ReactNode> = {}
  for (const cat of categories) {
    icons[cat] = getCategoryIcon(cat, className)
  }
  return icons
}
