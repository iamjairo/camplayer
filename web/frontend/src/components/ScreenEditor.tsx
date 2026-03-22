import React from 'react'
import { LayoutPicker } from './LayoutPicker'
import type { ScreenConfig, Device, LayoutId } from '../types/config'

interface ScreenEditorProps {
  screens: ScreenConfig[]
  devices: Device[]
  onChange: (screens: ScreenConfig[]) => void
}

export const ScreenEditor: React.FC<ScreenEditorProps> = ({ screens, devices, onChange }) => {
  const updateScreen = (idx: number, patch: Partial<ScreenConfig>) => {
    onChange(screens.map((s, i) => (i === idx ? { ...s, ...patch } : s)))
  }

  // Build a flat list of "device:channel" options
  const channelOptions: { label: string; value: string }[] = []
  for (const dev of devices) {
    for (const ch of dev.channels) {
      channelOptions.push({
        label: `${dev.name} › ${ch.name}`,
        value: `${dev.id}:${ch.id}`,
      })
    }
  }
  channelOptions.unshift({ label: '— empty —', value: ':' })

  return (
    <div className="space-y-4">
      {screens.map((screen, sIdx) => (
        <div key={screen.screen_idx} className="border border-zinc-700 rounded bg-zinc-900 p-3">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-white">Screen {screen.screen_idx}</span>
            <div className="flex items-center gap-3 text-xs text-zinc-400">
              <label className="flex items-center gap-1">
                Display
                <select
                  value={screen.display_idx}
                  onChange={e =>
                    updateScreen(sIdx, { display_idx: parseInt(e.target.value) })
                  }
                  className="ml-1 bg-zinc-800 border border-zinc-700 text-white text-xs rounded px-1 py-0.5 focus:outline-none"
                >
                  <option value={0}>HDMI0</option>
                  <option value={1}>HDMI1</option>
                </select>
              </label>
              <label className="flex items-center gap-1">
                Show
                <input
                  type="number"
                  min={0}
                  value={screen.displaytime}
                  onChange={e =>
                    updateScreen(sIdx, { displaytime: parseInt(e.target.value) || 0 })
                  }
                  className="ml-1 w-14 bg-zinc-800 border border-zinc-700 text-white text-xs rounded px-1 py-0.5 focus:outline-none text-center"
                />
                s
              </label>
            </div>
          </div>

          {/* Layout picker */}
          <div className="mb-3">
            <div className="text-xs text-zinc-500 mb-1.5">Layout</div>
            <LayoutPicker
              value={screen.layout as LayoutId}
              onChange={id => updateScreen(sIdx, { layout: id })}
            />
          </div>

          {/* Window assignments */}
          <div>
            <div className="text-xs text-zinc-500 mb-1.5">Windows</div>
            <div className="space-y-1">
              {screen.windows.map((win, wIdx) => (
                <div key={win.window_idx} className="flex items-center gap-2">
                  <span className="text-xs text-zinc-600 font-mono w-6 text-right">
                    w{win.window_idx + 1}
                  </span>
                  <select
                    value={`${win.device_id}:${win.channel_id}`}
                    onChange={e => {
                      const [device_id, channel_id] = e.target.value.split(':')
                      const label = channelOptions.find(o => o.value === e.target.value)?.label ?? ''
                      const windows = screen.windows.map((w, wi) =>
                        wi === wIdx
                          ? { ...w, device_id: device_id ?? '', channel_id: channel_id ?? '', display_name: label }
                          : w,
                      )
                      updateScreen(sIdx, { windows })
                    }}
                    className="flex-1 bg-zinc-800 border border-zinc-700 text-white text-xs rounded px-2 py-1 focus:outline-none focus:border-blue-500"
                  >
                    {channelOptions.map(opt => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
