/**
 * ChatHeader — Chat panel top bar with title, model selector, prompt selector,
 * scope indicator, questions toggle, and retrieval settings (Reranker / Top-K / Auto-Eval).
 *
 * Usage: <ChatHeader sessionBooks={books} totalBookCount={67} ... />
 */

import { Lightbulb, X } from "lucide-react";
import type { ModelInfo } from "@/features/shared/types";
import type { BookBase } from "@/features/shared/books";
import type { PersonaInfo } from "@/features/shared/consultingApi";
import CountrySelector from "@/features/shared/components/CountrySelector";
import LanguageSelector from "@/features/shared/components/LanguageSelector";
import PersonaPicker from "./PersonaPicker";

// ============================================================
// Mini Toggle — compact switch for boolean settings
// ============================================================
function MiniToggle({
  enabled,
  onChange,
  disabled,
  label,
  title,
}: {
  enabled: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  label: string;
  title?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      aria-label={label}
      title={title ?? label}
      disabled={disabled}
      onClick={() => onChange(!enabled)}
      className={`relative inline-flex h-[18px] w-[32px] shrink-0 items-center rounded-full border transition-colors duration-200 ${
        enabled
          ? "border-primary/40 bg-primary"
          : "border-border bg-muted/80"
      } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
    >
      <span
        className={`inline-block h-[14px] w-[14px] rounded-full bg-white shadow-sm transition-transform duration-200 ${
          enabled ? "translate-x-[15px]" : "translate-x-[1px]"
        }`}
      />
    </button>
  );
}

// ============================================================
// Types
// ============================================================
interface ChatHeaderProps {
  sessionBooks: BookBase[];
  totalBookCount: number;
  selectedModel: string;
  models: ModelInfo[];
  loading: boolean;
  onModelChange: (model: string, provider?: string) => void;
  onNewChat: () => void;
  onClearScope?: () => void;
  showQuestions?: boolean;
  onToggleQuestions?: () => void;
  personas: PersonaInfo[];
  selectedPersonaSlug: string | null;
  modeLocked: boolean;
  onPersonaChange: (slug: string) => void;
  /** Retrieval settings */
  topK: number;
  rerankerEnabled: boolean;
  autoEvaluate: boolean;
  onTopKChange: (value: number) => void;
  onRerankerChange: (enabled: boolean) => void;
  onAutoEvaluateChange: (enabled: boolean) => void;
}

// ============================================================
// Component
// ============================================================
export default function ChatHeader({
  sessionBooks,
  totalBookCount,
  selectedModel,
  models,
  loading,
  onModelChange,
  onNewChat,
  onClearScope,
  showQuestions,
  onToggleQuestions,
  personas,
  selectedPersonaSlug,
  modeLocked,
  onPersonaChange,
  topK,
  rerankerEnabled,
  autoEvaluate,
  onTopKChange,
  onRerankerChange,
  onAutoEvaluateChange,
}: ChatHeaderProps) {
  const isScoped = sessionBooks.length < totalBookCount && totalBookCount > 0;

  return (
    <div className="shrink-0 border-b border-border bg-card px-4 py-2">
      <div className="flex items-center gap-3">
        {/* Title + scope */}
        <div className="min-w-0 shrink-0">
          <h2 className="text-sm font-semibold text-foreground">EcDev Research</h2>
          <div className="flex items-center gap-1.5">
            {isScoped ? (
              <>
                <span className="text-[11px] text-primary font-medium">
                  {sessionBooks.length === 1
                    ? sessionBooks[0].title
                    : `Searching ${sessionBooks.length} of ${totalBookCount} documents`}
                </span>
                {onClearScope && (
                  <button
                    type="button"
                    onClick={onClearScope}
                    className="flex items-center gap-0.5 text-[10px] text-muted-foreground hover:text-foreground bg-muted hover:bg-muted-foreground/20 rounded px-1.5 py-0.5 transition-colors"
                    title="Search all documents"
                  >
                    <X className="h-2.5 w-2.5" />
                    <span>All</span>
                  </button>
                )}
              </>
            ) : (
              <p className="text-[11px] text-muted-foreground">
                {`Searching all ${sessionBooks.length} documents`}
              </p>
            )}
          </div>
        </div>

        <div className="flex-1" />

        {/* ── All controls in one row ── */}
        <div className="flex shrink-0 items-center gap-2">
          {/* Persona */}
          <PersonaPicker
            personas={personas}
            selectedSlug={selectedPersonaSlug}
            disabled={loading || modeLocked || personas.length === 0}
            disabledTitle={modeLocked ? "Persona is locked for this conversation" : undefined}
            onSelect={onPersonaChange}
          />

          {/* Model — grouped by family (local) + cloud */}
          <select
            className="h-7 rounded-md border border-border bg-background px-2 text-[11px] font-medium text-foreground outline-none transition focus:border-primary"
            value={selectedModel}
            onChange={(event) => {
              const name = event.target.value;
              const found = models.find((m) => m.name === name);
              onModelChange(name, found?.provider);
            }}
            disabled={loading || models.length === 0}
            suppressHydrationWarning
          >
            {models.length === 0 ? (
              <option value={selectedModel} suppressHydrationWarning>{selectedModel}</option>
            ) : (
              (() => {
                // Filter out embedding models (nomic-embed-*, mxbai-embed-*, bge-*, etc.)
                const chatModels = models.filter(
                  (m) => !m.name.toLowerCase().includes("embed")
                );

                // Parse parameter size (in billions) from Ollama tag
                // e.g. "qwen3.6:35b" → 35, "phi4-mini:3.8b" → 3.8, "gemma4:e2b" → 2
                const parseParamB = (name: string): number | null => {
                  const tag = name.split(":")[1] || "";
                  // Match leading number like "35b", "3.8b", or after prefix like "e2b" → 2
                  const m = tag.match(/^(\d+\.?\d*)[bB]/);
                  if (m) return parseFloat(m[1]);
                  // Handle "e2b" / "e4b" style (gemma4)
                  const m2 = tag.match(/[a-z](\d+\.?\d*)[bB]/);
                  if (m2) return parseFloat(m2[1]);
                  return null;
                };

                // 8GB VRAM cutoff: hide local models >14B (they won't fit)
                const MAX_PARAM_B = 14;

                // Separate local (ollama) vs cloud models
                const local = chatModels.filter((m) => {
                  if (m.provider && m.provider !== "ollama") return false;
                  const paramB = parseParamB(m.name);
                  // If we can parse size and it's too large, filter it out
                  if (paramB !== null && paramB > MAX_PARAM_B) return false;
                  return true;
                });
                const cloud = chatModels.filter(
                  (m) => m.provider && m.provider !== "ollama"
                );

                // Infer family from model name for grouping
                const inferFamily = (name: string): string => {
                  const n = name.toLowerCase();
                  if (n.startsWith("qwen"))     return "Qwen";
                  if (n.startsWith("phi"))      return "Phi";
                  if (n.startsWith("gemma"))    return "Gemma";
                  if (n.startsWith("llama"))    return "Llama";
                  if (n.startsWith("deepseek")) return "DeepSeek";
                  if (n.startsWith("mistral"))  return "Mistral";
                  if (n.startsWith("yi"))       return "Yi";
                  return "Other";
                };

                // Group local models by family, preserving order
                const familyMap = new Map<string, typeof local>();
                for (const m of local) {
                  const fam = inferFamily(m.name);
                  if (!familyMap.has(fam)) familyMap.set(fam, []);
                  familyMap.get(fam)!.push(m);
                }



                return (
                  <>
                    {/* Cloud models first (default gpt-4o-mini) */}
                    {cloud.length > 0 && (
                      <optgroup label="Cloud">
                        {cloud.map((m) => (
                          <option key={m.name} value={m.name}>
                            {m.name}{m.is_default ? " ✦" : ""}
                          </option>
                        ))}
                      </optgroup>
                    )}
                    {/* Local models grouped by family */}
                    {[...familyMap.entries()].map(([family, familyModels]) => (
                      <optgroup key={family} label={family}>
                        {familyModels.map((m) => (
                          <option key={m.name} value={m.name}>
                            {m.name}{m.is_default ? " ✦" : ""}
                          </option>
                        ))}
                      </optgroup>
                    ))}
                  </>
                );
              })()
            )}
          </select>

          <div className="h-4 w-px bg-border" />

          {/* Top-K */}
          <div className="flex items-center gap-1.5">
            <label className="text-[10px] font-medium text-muted-foreground" title="Number of document chunks retrieved per query">K</label>
            <input type="range" min={3} max={20} step={1} value={topK} onChange={(e) => onTopKChange(Number(e.target.value))} disabled={loading} className="h-1 w-14 cursor-pointer accent-primary" />
            <span className="w-4 text-center text-[10px] font-bold tabular-nums text-foreground">{topK}</span>
          </div>

          {/* Reranker */}
          <div className="flex items-center gap-1.5">
            <label className="text-[10px] font-medium text-muted-foreground" title="LLMRerank — re-scores chunks with LLM">Rerank</label>
            <MiniToggle enabled={rerankerEnabled} onChange={onRerankerChange} disabled={loading} label="Enable LLM Reranker" />
          </div>

          {/* Auto-Eval */}
          <div className="flex items-center gap-1.5">
            <label className="text-[10px] font-medium text-muted-foreground" title="Auto-evaluate each response">Eval</label>
            <MiniToggle enabled={autoEvaluate} onChange={onAutoEvaluateChange} disabled={loading} label="Auto-evaluate responses" />
          </div>

          {/* Questions toggle */}
          {onToggleQuestions && !showQuestions && (
            <>
              <div className="h-4 w-px bg-border" />
              <button
                type="button"
                onClick={onToggleQuestions}
                className={`flex items-center justify-center h-7 w-7 rounded-md border transition-colors ${
                  showQuestions ? 'bg-primary/10 text-primary border-primary/30' : 'border-border text-muted-foreground hover:bg-accent'
                }`}
                title="Show suggested questions"
              >
                <Lightbulb size={14} />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
