import { useCallback, useEffect, useState } from 'react'
import { useConfig } from './hooks/useConfig'
import { useStreams } from './hooks/useStreams'
import { useLayoutControl } from './hooks/useLayoutControl'
import { NavBar } from './components/NavBar'
import { GridLayout } from './components/GridLayout'
import { SettingsPanel } from './components/SettingsPanel'
import type { CamplayerConfig } from './types/config'

// Loading skeleton — shown while config is being fetched
function LoadingSkeleton() {
  return (
    <div className="flex flex-col h-full bg-black">
      <div className="h-12 bg-zinc-900 border-b border-zinc-800 flex items-center px-4 gap-3 animate-pulse flex-shrink-0">
        <div className="w-5 h-5 rounded bg-zinc-700" />
        <div className="w-24 h-4 rounded bg-zinc-700" />
        <div className="flex gap-2 flex-1">
          {[1, 2].map(i => (
            <div key={i} className="w-16 h-6 rounded bg-zinc-800" />
          ))}
        </div>
      </div>
      <div className="flex-1 grid grid-cols-2 grid-rows-2 gap-0.5 p-0.5">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-zinc-900 animate-pulse" />
        ))}
      </div>
    </div>
  )
}

// Error state
function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full bg-black text-center p-8">
      <div className="text-red-400 text-4xl mb-4">⚠</div>
      <div className="text-white font-semibold mb-2">Could not load configuration</div>
      <div className="text-zinc-500 text-sm mb-6 max-w-sm">{message}</div>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded transition-colors"
      >
        Retry
      </button>
    </div>
  )
}

export default function App() {
  const { config, isLoading, error, saveConfig, mutate } = useConfig()
  const { statuses, wsConnected, overallStatus } = useStreams()
  const { nextScreen, prevScreen, setScreen } = useLayoutControl()

  const [activeScreenIdx, setActiveScreenIdx] = useState(0)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  // Keyboard nav: ArrowLeft/Right for screen switching
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (settingsOpen) return
      if (e.key === 'ArrowRight') {
        handleNextScreen()
      } else if (e.key === 'ArrowLeft') {
        handlePrevScreen()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  })

  const handleNextScreen = useCallback(() => {
    if (!config) return
    const next = (activeScreenIdx + 1) % config.screens.length
    setActiveScreenIdx(next)
    nextScreen(config.screens[activeScreenIdx]?.display_idx ?? 0).catch(() => {})
  }, [activeScreenIdx, config, nextScreen])

  const handlePrevScreen = useCallback(() => {
    if (!config) return
    const prev = (activeScreenIdx - 1 + config.screens.length) % config.screens.length
    setActiveScreenIdx(prev)
    prevScreen(config.screens[activeScreenIdx]?.display_idx ?? 0).catch(() => {})
  }, [activeScreenIdx, config, prevScreen])

  const handleSelectScreen = useCallback(
    (idx: number) => {
      setActiveScreenIdx(idx)
      if (config) {
        setScreen(idx, config.screens[idx]?.display_idx ?? 0).catch(() => {})
      }
    },
    [config, setScreen],
  )

  const handleSave = async (next: CamplayerConfig) => {
    setSaving(true)
    try {
      await saveConfig(next)
      setSettingsOpen(false)
    } finally {
      setSaving(false)
    }
  }

  if (isLoading) return <LoadingSkeleton />
  if (error) return <ErrorState message={error.message} onRetry={() => mutate()} />
  if (!config) return null

  const activeScreen = config.screens[activeScreenIdx] ?? config.screens[0]

  // Build streamId map: "device_id:channel_id" → stream ID for go2rtc
  // go2rtc stream names follow the convention "<device_id>_<channel_id>"
  const streamIdMap: Record<string, string> = {}
  for (const device of config.devices) {
    for (const channel of device.channels) {
      const key = `${device.id}:${channel.id}`
      streamIdMap[key] = `${device.id}_${channel.id}`
    }
  }

  // Count active/total streams
  const totalStreams = activeScreen?.windows.length ?? 0
  const playingStreams = Object.values(statuses).filter(s => s.playstate === 3).length

  return (
    <div className="flex flex-col h-full bg-black">
      <NavBar
        screens={config.screens}
        activeScreenIdx={activeScreenIdx}
        onSelectScreen={handleSelectScreen}
        onSettingsOpen={() => setSettingsOpen(true)}
        wsConnected={wsConnected}
        overallStatus={overallStatus}
        streamCount={playingStreams > 0 ? playingStreams : totalStreams}
      />

      <main className="flex-1 min-h-0">
        {activeScreen ? (
          <GridLayout screen={activeScreen} streamIdMap={streamIdMap} />
        ) : (
          <div className="flex items-center justify-center h-full text-zinc-600">
            No screens configured
          </div>
        )}
      </main>

      {settingsOpen && (
        <SettingsPanel
          config={config}
          open={settingsOpen}
          saving={saving}
          onClose={() => setSettingsOpen(false)}
          onSave={handleSave}
        />
      )}
    </div>
  )
}
