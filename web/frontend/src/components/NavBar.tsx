import React from 'react'
import { Camera, Settings, Wifi, WifiOff } from 'lucide-react'
import type { ScreenConfig } from '../types/config'
import type { UseStreamsResult } from '../hooks/useStreams'

interface NavBarProps {
  screens: ScreenConfig[]
  activeScreenIdx: number
  onSelectScreen: (idx: number) => void
  onSettingsOpen: () => void
  wsConnected: UseStreamsResult['wsConnected']
  overallStatus: UseStreamsResult['overallStatus']
  streamCount: number
}

export const NavBar: React.FC<NavBarProps> = ({
  screens,
  activeScreenIdx,
  onSelectScreen,
  onSettingsOpen,
  wsConnected,
  overallStatus,
  streamCount,
}) => {
  const statusColour =
    overallStatus === 'healthy'
      ? 'text-green-400'
      : overallStatus === 'degraded'
      ? 'text-yellow-400'
      : overallStatus === 'error'
      ? 'text-red-400'
      : 'text-zinc-500'

  return (
    <header className="flex items-center h-12 px-3 bg-zinc-900 border-b border-zinc-800 flex-shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2 text-blue-400 mr-4 select-none">
        <Camera size={20} />
        <span className="font-semibold text-sm text-white tracking-wide">Camplayer</span>
      </div>

      {/* Screen tabs */}
      <nav className="flex items-center gap-1 flex-1 overflow-x-auto">
        {screens.map((screen, idx) => (
          <button
            key={screen.screen_idx}
            onClick={() => onSelectScreen(idx)}
            className={[
              'px-3 py-1 rounded text-xs font-medium whitespace-nowrap transition-colors',
              idx === activeScreenIdx
                ? 'bg-blue-600 text-white'
                : 'text-zinc-400 hover:text-white hover:bg-zinc-800',
            ].join(' ')}
          >
            Screen {screen.screen_idx}
          </button>
        ))}
      </nav>

      {/* Right section */}
      <div className="flex items-center gap-3 ml-3 flex-shrink-0">
        {/* Stream count badge */}
        <span className="text-xs text-zinc-400 font-mono">
          {streamCount} <span className="text-zinc-600">streams</span>
        </span>

        {/* WS connection indicator */}
        <span className={`${statusColour} flex items-center gap-1`} title={overallStatus}>
          {wsConnected ? <Wifi size={14} /> : <WifiOff size={14} />}
        </span>

        {/* Settings button */}
        <button
          onClick={onSettingsOpen}
          className="p-1.5 rounded text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
          title="Settings"
        >
          <Settings size={16} />
        </button>
      </div>
    </header>
  )
}
