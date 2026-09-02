"use client"
import { useState, useEffect, useCallback, useRef } from "react"

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number = 5000,
) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const refetch = useCallback(async () => {
    try {
      const result = await fetcherRef.current()
      setData(result)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refetch()
    const id = setInterval(() => {
      if (!document.hidden) refetch()
    }, intervalMs)
    return () => clearInterval(id)
  }, [refetch, intervalMs])

  return { data, error, loading, refetch }
}
