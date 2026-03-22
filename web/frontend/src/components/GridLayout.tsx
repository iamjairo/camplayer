import React, { useCallback, useEffect, useState } from 'react'
import { getLayout } from '../utils/layouts'
import { VideoCell } from './VideoCell'
import type { ScreenConfig } from '../types/config'

interface GridLayoutProps {
  screen: ScreenConfig
  /** Map from "device_id:channel_id" → go2rtc stream ID */
  streamIdMap: Record<string, string>
}

export const GridLayout: React.FC<GridLayoutProps> = ({ screen, streamIdMap }) => {
  const layout = getLayout(screen.layout)
  const [focusedWindow, setFocusedWindow] = useState<number | null>(null)

  // Keyboard shortcuts: ArrowLeft/Right for screen navigation (handled in App)
  // Escape to exit fullscreen focus
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setFocusedWindow(null)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const handleFocus = useCallback((windowIndex: number) => {
    setFocusedWindow(prev => (prev === windowIndex ? null : windowIndex))
  }, [])

  // Fullscreen single-cell mode
  if (focusedWindow !== null) {
    const win = screen.windows[focusedWindow]
    const streamKey = win ? `${win.device_id}:${win.channel_id}` : null
    const streamId = streamKey ? (streamIdMap[streamKey] ?? streamKey) : null
    return (
      <div
        className="fixed inset-0 z-50 bg-black"
        onClick={() => setFocusedWindow(null)}
      >
        <VideoCell
          streamId={streamId}
          cameraName={win?.display_name}
          windowIndex={focusedWindow}
          isLarge
          onFocus={handleFocus}
        />
        <div className="absolute top-2 right-2 z-50 text-xs bg-black/70 text-zinc-400 px-2 py-1 rounded">
          Press Esc or click to exit
        </div>
      </div>
    )
  }

  // CSS grid areas style
  const gridStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateAreas: layout.areas,
    gridTemplateColumns: `repeat(${layout.cols}, 1fr)`,
    gridTemplateRows: `repeat(${layout.rows}, 1fr)`,
    width: '100%',
    height: '100%',
    gap: '2px',
  }

  const cells = Array.from({ length: layout.windowCount }, (_, i) => {
    const win = screen.windows[i]
    const streamKey = win ? `${win.device_id}:${win.channel_id}` : null
    const streamId = streamKey ? (streamIdMap[streamKey] ?? streamKey) : null
    const isLarge = layout.largeWindows.includes(i + 1)

    return (
      <div
        key={i}
        style={{ gridArea: `w${i + 1}` }}
        className="min-h-0 min-w-0"
      >
        <VideoCell
          streamId={streamId}
          cameraName={win?.display_name}
          windowIndex={i}
          isLarge={isLarge}
          onFocus={handleFocus}
        />
      </div>
    )
  })

  return (
    <div style={gridStyle} className="bg-black">
      {cells}
    </div>
  )
}
