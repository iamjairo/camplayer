import React from 'react'
import type { WebRTCStatus } from '../hooks/useWebRTC'

interface StatusOverlayProps {
  status: WebRTCStatus
  streamId?: string | null
  onReconnect?: () => void
}

export const StatusOverlay: React.FC<StatusOverlayProps> = ({ status, streamId, onReconnect }) => {
  if (status === 'playing') return null

  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-zinc-900/90 z-10">
      {status === 'idle' && (
        <div className="text-center">
          <div className="text-zinc-500 text-sm mb-1">No stream</div>
          {streamId && (
            <div className="text-zinc-600 text-xs font-mono truncate max-w-[120px]">{streamId}</div>
          )}
        </div>
      )}

      {status === 'connecting' && (
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <div className="text-blue-400 text-xs">Connecting…</div>
        </div>
      )}

      {(status === 'error' || status === 'closed') && (
        <div className="text-center">
          <div className="text-red-400 text-2xl mb-1">⚠</div>
          <div className="text-red-400 text-xs mb-2">Stream error</div>
          {onReconnect && (
            <button
              onClick={onReconnect}
              className="text-xs px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded border border-zinc-700 transition-colors"
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  )
}
