'use client'

/**
 * GenerationProgress — step-by-step progress tracker while LLM generates questions.
 * 问题生成进度条组件 — 带步骤动画 + 计时器。
 *
 * Extracted from chat/panel/WelcomeScreen so the questions module is self-contained.
 */

import { useState, useEffect } from 'react'
import { Database, Layers, Bot, Sparkles, Check, Loader2 } from 'lucide-react'

interface StepDef {
  label: string
  icon: React.ElementType
  autoAdvanceMs: number // 0 = wait for parent unmount
}

const GENERATION_STEPS: StepDef[] = [
  { label: 'Sampling chunks from books', icon: Database, autoAdvanceMs: 1500 },
  { label: 'Building prompt context',    icon: Layers,   autoAdvanceMs: 2000 },
  { label: 'Calling LLM model',          icon: Bot,      autoAdvanceMs: 0 },
  { label: 'Parsing & formatting',       icon: Sparkles, autoAdvanceMs: 1000 },
]

export default function GenerationProgress() {
  const [currentStep, setCurrentStep] = useState(0)
  const [totalElapsed, setTotalElapsed] = useState(0)
  const [stepTimestamps, setStepTimestamps] = useState<number[]>(() => [Date.now()])
  const startRef = useState(() => Date.now())[0]

  // Auto-advance timed steps
  useEffect(() => {
    const step = GENERATION_STEPS[currentStep]
    if (!step || step.autoAdvanceMs === 0) return

    const timer = setTimeout(() => {
      if (currentStep < GENERATION_STEPS.length - 1) {
        setStepTimestamps((prev) => [...prev, Date.now()])
        setCurrentStep((s) => s + 1)
      }
    }, step.autoAdvanceMs)
    return () => clearTimeout(timer)
  }, [currentStep])

  // Total elapsed counter
  useEffect(() => {
    const iv = setInterval(() => setTotalElapsed(Math.floor((Date.now() - startRef) / 1000)), 200)
    return () => clearInterval(iv)
  }, [startRef])

  // Per-step durations
  const stepDurations = GENERATION_STEPS.map((_, i) => {
    if (i >= stepTimestamps.length) return null // not started
    const start = stepTimestamps[i]
    const end = i + 1 < stepTimestamps.length ? stepTimestamps[i + 1] : Date.now()
    return ((end - start) / 1000).toFixed(1)
  })

  const pct = Math.min(((currentStep + 0.5) / GENERATION_STEPS.length) * 100, 95)

  return (
    <div className="w-full max-w-md mx-auto">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
          <span>Generating study questions…</span>
        </div>
        <span className="text-[11px] tabular-nums font-mono text-muted-foreground">
          {totalElapsed}s
        </span>
      </div>

      {/* Progress bar */}
      <div className="mb-4 h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Steps */}
      <div className="space-y-1">
        {GENERATION_STEPS.map((step, i) => {
          const isDone = i < currentStep
          const isActive = i === currentStep
          const Icon = step.icon
          const duration = stepDurations[i]

          return (
            <div
              key={i}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 transition-all duration-300 ${
                isActive
                  ? 'bg-primary/5 border border-primary/20 shadow-sm'
                  : isDone
                  ? 'bg-transparent'
                  : 'bg-transparent opacity-40'
              }`}
            >
              {/* Step number circle or status */}
              <div className="relative w-6 h-6 flex items-center justify-center shrink-0">
                {isDone ? (
                  <div className="w-6 h-6 rounded-full bg-emerald-500/15 flex items-center justify-center">
                    <Check className="h-3.5 w-3.5 text-emerald-500" strokeWidth={3} />
                  </div>
                ) : isActive ? (
                  <div className="w-6 h-6 rounded-full border-2 border-primary/30 flex items-center justify-center">
                    <div className="h-3 w-3 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                  </div>
                ) : (
                  <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center">
                    <span className="text-[10px] font-bold text-muted-foreground">{i + 1}</span>
                  </div>
                )}
              </div>

              {/* Icon */}
              <Icon className={`h-4 w-4 shrink-0 ${
                isDone ? 'text-emerald-500' : isActive ? 'text-primary' : 'text-muted-foreground'
              }`} />

              {/* Label */}
              <span className={`text-xs flex-1 ${
                isActive ? 'text-foreground font-medium' : 'text-muted-foreground'
              }`}>
                {step.label}
              </span>

              {/* Duration */}
              {duration && (
                <span className={`text-[10px] tabular-nums font-mono px-1.5 py-0.5 rounded ${
                  isDone
                    ? 'text-emerald-500 bg-emerald-500/10'
                    : isActive
                    ? 'text-primary bg-primary/10'
                    : 'text-muted-foreground'
                }`}>
                  {duration}s
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
