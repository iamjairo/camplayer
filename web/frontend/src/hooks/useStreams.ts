import { useEffect, useRef, useState } from 'react'
import type { StreamStatusMap, WsMessage } from '../types/stream'

const WS_URL = '/ws/status'
const RECONNECT_INITIAL_MS = 2_000
const RECONNECT_MAX_MS = 30_000

export interface UseStreamsResult {
  statuses: StreamStatusMap
  wsConnected: boolean
  overallStatus: 'healthy' | 'degraded' | 'error' | 'unknown'
}

export function useStreams(): UseStreamsResult {
  const [statuses, setStatuses] = useState<StreamStatusMap>({})
  const [wsConnected, setWsConnected] = useState(false)
  const [overallStatus, setOverallStatus] = useState<UseStreamsResult['overallStatus']>('unknown')
  const retryDelayRef = useRef(RECONNECT_INITIAL_MS)
  const wsRef = useRef<WebSocket | null>(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true

    function connect() {
      if (!mountedRef.current) return

      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const ws = new WebSocket(`${proto}//${window.location.host}${WS_URL}`)
      wsRef.current = ws

      ws.onopen = () => {
        if (!mountedRef.current) return
        setWsConnected(true)
        retryDelayRef.current = RECONNECT_INITIAL_MS
      }

      ws.onmessage = (e: MessageEvent) => {
        if (!mountedRef.current) return
        try {
          const msg = JSON.parse(e.data as string) as WsMessage
          if (msg.type === 'stream_status') {
            const key = `${msg.display_idx}:${msg.screen_idx}:${msg.window_idx}`
            setStatuses(prev => ({ ...prev, [key]: msg }))
          } else if (msg.type === 'heartbeat') {
            setOverallStatus(msg.overall_status)
          }
        } catch {
          // ignore
        }
      }

      ws.onclose = () => {
        if (!mountedRef.current) return
        setWsConnected(false)
        const delay = retryDelayRef.current
        retryDelayRef.current = Math.min(delay * 2, RECONNECT_MAX_MS)
        setTimeout(connect, delay)
      }

      ws.onerror = () => ws.close()
    }

    connect()

    return () => {
      mountedRef.current = false
      wsRef.current?.close()
    }
  }, [])

  return { statuses, wsConnected, overallStatus }
}
