/**
 * useQueryEngine — Query engine debug hook (sync + streaming).
 *
 * Usage: const { result, loading, error, query, queryStream, reset } = useQueryEngine()
 */

'use client'

import { useState, useCallback, useRef } from 'react'
import type { QueryRequest, QueryResponse } from './types'
import { queryTextbook, queryTextbookStream } from './api'

// ============================================================
// Types
// ============================================================
export interface UseQueryEngineState {
  result: QueryResponse | null
  streamingText: string
  loading: boolean
  error: Error | null
}

// ============================================================
// Hook
// ============================================================
export function useQueryEngine() {

  // ==========================================================
  // State
  // ==========================================================
  const [state, setState] = useState<UseQueryEngineState>({
    result: null,
    streamingText: '',
    loading: false,
    error: null,
  })

  const abortRef = useRef<AbortController | null>(null)

  // ==========================================================
  // Sync query
  // ==========================================================
  const query = useCallback(async (req: QueryRequest) => {
    abortRef.current?.abort()
    setState({ result: null, streamingText: '', loading: true, error: null })

    try {
      const result = await queryTextbook(req)
      setState({ result, streamingText: '', loading: false, error: null })
      return result
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err))
      setState((s) => ({ ...s, loading: false, error }))
      return null
    }
  }, [])

  // ==========================================================
  // Streaming query
  // ==========================================================
  const queryStream = useCallback(async (req: QueryRequest) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setState({ result: null, streamingText: '', loading: true, error: null })

    await queryTextbookStream(req, {
      signal: controller.signal,

      onToken: (token: string) => {
        setState((s) => ({
          ...s,
          streamingText: s.streamingText + token,
        }))
      },

      onRetrievalDone: () => {
        // Retrieval phase done — sources available via streaming state
      },

      onDone: (result: QueryResponse) => {
        setState({
          result,
          streamingText: result.answer,
          loading: false,
          error: null,
        })
      },

      onError: (error: Error) => {
        setState((s) => ({ ...s, loading: false, error }))
      },
    })
  }, [])

  // ==========================================================
  // Reset state
  // ==========================================================
  const reset = useCallback(() => {
    abortRef.current?.abort()
    setState({ result: null, streamingText: '', loading: false, error: null })
  }, [])

  // ==========================================================
  // Abort current request
  // ==========================================================
  const abort = useCallback(() => {
    abortRef.current?.abort()
    setState((s) => ({ ...s, loading: false }))
  }, [])

  // ==========================================================
  // Return
  // ==========================================================
  return {
    result: state.result,
    streamingText: state.streamingText,
    loading: state.loading,
    error: state.error,
    query,
    queryStream,
    reset,
    abort,
  }
}
