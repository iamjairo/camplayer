import { useCallback, useEffect, useRef, useState } from 'react'
import { connectWebRTC } from '../utils/go2rtc'
import type { WebRTCState } from '../utils/go2rtc'

export type WebRTCStatus = WebRTCState | 'idle'

const BACKOFF_INITIAL_MS = 2_000
const BACKOFF_MAX_MS = 30_000

export interface UseWebRTCResult {
  videoRef: React.RefObject<HTMLVideoElement>
  status: WebRTCStatus
  reconnect: () => void
}

export function useWebRTC(streamId: string | null): UseWebRTCResult {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [status, setStatus] = useState<WebRTCStatus>('idle')
  const handleRef = useRef<{ close(): void } | null>(null)
  const backoffRef = useRef(BACKOFF_INITIAL_MS)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  const clearRetry = () => {
    if (retryTimerRef.current !== null) {
      clearTimeout(retryTimerRef.current)
      retryTimerRef.current = null
    }
  }

  const teardown = useCallback(() => {
    clearRetry()
    handleRef.current?.close()
    handleRef.current = null
  }, [])

  const start = useCallback(() => {
    if (!mountedRef.current || !streamId || !videoRef.current) return
    teardown()

    const handle = connectWebRTC(
      streamId,
      videoRef.current,
      (state: WebRTCState) => {
        if (!mountedRef.current) return
        setStatus(state)
        if (state === 'error') {
          // Exponential backoff reconnect
          const delay = backoffRef.current
          backoffRef.current = Math.min(delay * 2, BACKOFF_MAX_MS)
          retryTimerRef.current = setTimeout(() => {
            if (mountedRef.current) start()
          }, delay)
        } else if (state === 'playing') {
          backoffRef.current = BACKOFF_INITIAL_MS
        }
      },
    )
    handleRef.current = handle
  }, [streamId, teardown])

  // Restart when streamId changes
  useEffect(() => {
    mountedRef.current = true
    if (streamId) {
      backoffRef.current = BACKOFF_INITIAL_MS
      start()
    } else {
      teardown()
      setStatus('idle')
    }
    return () => {
      mountedRef.current = false
      teardown()
    }
  }, [streamId, start, teardown])

  const reconnect = useCallback(() => {
    backoffRef.current = BACKOFF_INITIAL_MS
    start()
  }, [start])

  return { videoRef, status, reconnect }
}
