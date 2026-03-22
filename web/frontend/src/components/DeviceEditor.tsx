import React, { useState } from 'react'
import { Plus, Trash2, ChevronDown, ChevronRight } from 'lucide-react'
import type { Device, Channel } from '../types/config'

interface DeviceEditorProps {
  devices: Device[]
  onChange: (devices: Device[]) => void
}

function emptyChannel(idx: number): Channel {
  return { id: `channel${idx}`, name: `Channel ${idx}`, streams: [], force_udp: false }
}

function emptyDevice(idx: number): Device {
  return { id: `device${idx}`, name: `Device ${idx}`, channels: [emptyChannel(1)] }
}

export const DeviceEditor: React.FC<DeviceEditorProps> = ({ devices, onChange }) => {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const toggle = (id: string) => setExpanded(prev => ({ ...prev, [id]: !prev[id] }))

  const addDevice = () => {
    onChange([...devices, emptyDevice(devices.length + 1)])
  }

  const removeDevice = (idx: number) => {
    onChange(devices.filter((_, i) => i !== idx))
  }

  const updateDevice = (idx: number, patch: Partial<Device>) => {
    onChange(devices.map((d, i) => (i === idx ? { ...d, ...patch } : d)))
  }

  const addChannel = (deviceIdx: number) => {
    const dev = devices[deviceIdx]
    const newCh = emptyChannel(dev.channels.length + 1)
    updateDevice(deviceIdx, { channels: [...dev.channels, newCh] })
  }

  const removeChannel = (deviceIdx: number, chIdx: number) => {
    const dev = devices[deviceIdx]
    updateDevice(deviceIdx, { channels: dev.channels.filter((_, i) => i !== chIdx) })
  }

  const updateChannel = (deviceIdx: number, chIdx: number, patch: Partial<Channel>) => {
    const dev = devices[deviceIdx]
    updateDevice(deviceIdx, {
      channels: dev.channels.map((ch, i) => (i === chIdx ? { ...ch, ...patch } : ch)),
    })
  }

  return (
    <div className="space-y-2">
      {devices.map((device, dIdx) => (
        <div key={device.id} className="border border-zinc-700 rounded bg-zinc-900">
          {/* Device header */}
          <div className="flex items-center gap-2 px-3 py-2">
            <button onClick={() => toggle(device.id)} className="text-zinc-400 hover:text-white">
              {expanded[device.id] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>
            <input
              className="flex-1 bg-zinc-800 text-white text-sm px-2 py-1 rounded border border-zinc-700 focus:outline-none focus:border-blue-500"
              value={device.name}
              onChange={e => updateDevice(dIdx, { name: e.target.value })}
              placeholder="Device name"
            />
            <span className="text-zinc-600 text-xs font-mono">{device.id}</span>
            <button
              onClick={() => removeDevice(dIdx)}
              className="text-zinc-600 hover:text-red-400 transition-colors"
            >
              <Trash2 size={14} />
            </button>
          </div>

          {/* Channels */}
          {expanded[device.id] && (
            <div className="px-3 pb-2 space-y-2 border-t border-zinc-800 pt-2">
              {device.channels.map((ch, cIdx) => (
                <div key={ch.id} className="flex items-start gap-2">
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <input
                        className="flex-1 bg-zinc-800 text-white text-xs px-2 py-1 rounded border border-zinc-700 focus:outline-none focus:border-blue-500"
                        value={ch.name}
                        onChange={e => updateChannel(dIdx, cIdx, { name: e.target.value })}
                        placeholder="Channel name"
                      />
                      <span className="text-zinc-600 text-xs font-mono">{ch.id}</span>
                    </div>
                    {/* Stream URLs */}
                    {ch.streams.map((s, sIdx) => (
                      <input
                        key={sIdx}
                        className="w-full bg-zinc-800 text-zinc-300 text-xs px-2 py-1 rounded border border-zinc-700 font-mono focus:outline-none focus:border-blue-500"
                        value={s.url}
                        onChange={e => {
                          const streams = [...ch.streams]
                          streams[sIdx] = { ...streams[sIdx], url: e.target.value }
                          updateChannel(dIdx, cIdx, { streams })
                        }}
                        placeholder={`rtsp://... (quality ${s.quality_level})`}
                      />
                    ))}
                    {ch.streams.length === 0 && (
                      <div className="text-zinc-600 text-xs italic">No stream URLs configured</div>
                    )}
                  </div>
                  <button
                    onClick={() => removeChannel(dIdx, cIdx)}
                    className="text-zinc-600 hover:text-red-400 mt-1 transition-colors"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
              <button
                onClick={() => addChannel(dIdx)}
                className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
              >
                <Plus size={12} /> Add channel
              </button>
            </div>
          )}
        </div>
      ))}

      <button
        onClick={addDevice}
        className="flex items-center gap-1.5 text-sm text-blue-400 hover:text-blue-300 transition-colors py-1"
      >
        <Plus size={14} /> Add device
      </button>
    </div>
  )
}
