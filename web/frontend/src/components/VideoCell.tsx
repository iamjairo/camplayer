import React, { useCallback, useState } from 'react'
import { useWebRTC } from '../hooks/useWebRTC'
import { StatusOverlay } from './StatusOverlay'

interface VideoCellProps {
  streamId: string | null
  cameraName?: string
  windowIndex: number
  isLarge?: boolean
  onFocus?: (windowIndex: number) => void
}

export const VideoCell: React.FC<VideoCellProps> = ({
  streamId,
  cameraName,
  windowIndex,
  isLarge = false,
  onFocus,
}) => {
  const { videoRef, status, reconnect } = useWebRTC(streamId)
  const [hovered, setHovered] = useState(false)

  const handleClick = useCallback(() => {
    onFocus?.(windowIndex)
  }, [onFocus, windowIndex])

  // Status indicator dot colour
  const dotClass =
    status === 'playing'
      ? 'bg-green-500'
      : status === 'connecting'
      ? 'bg-yellow-500 animate-pulse'
      : status === 'error' || status === 'closed'
      ? 'bg-red-500'
      : 'bg-zinc-600'

  return (
    <div
      className={[
        'relative w-full h-full bg-zinc-950 border border-zinc-800 overflow-hidden cursor-pointer select-none',
        hovered ? 'border-blue-500' : '',
        isLarge ? 'border-zinc-700' : '',
      ].join(' ')}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={handleClick}
    >
      {/* Video element */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full h-full object-cover"
      />

      {/* Loading / error overlay */}
      <StatusOverlay status={status} streamId={streamId} onReconnect={reconnect} />

      {/* Bottom-left camera name + status dot */}
      {(cameraName || streamId) && (
        <div className="absolute bottom-0 left-0 right-0 flex items-center gap-1.5 px-2 py-1 bg-black/60 z-20">
          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dotClass}`} />
          <span className="text-white text-xs truncate font-mono">
            {cameraName ?? streamId}
          </span>
        </div>
      )}

      {/* Hover focus hint */}
      {hovered && status === 'playing' && (
        <div className="absolute top-1 right-1 z-20 text-xs bg-black/60 text-zinc-400 px-1.5 py-0.5 rounded">
          ⤢ focus
        </div>
      )}
    </div>
  )
}
