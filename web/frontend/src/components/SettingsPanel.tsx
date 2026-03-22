import React, { useState } from 'react'
import { X, Save, Loader2 } from 'lucide-react'
import { DeviceEditor } from './DeviceEditor'
import { ScreenEditor } from './ScreenEditor'
import type { CamplayerConfig } from '../types/config'

type Tab = 'cameras' | 'screens' | 'advanced'

interface SettingsPanelProps {
  config: CamplayerConfig
  open: boolean
  saving: boolean
  onClose: () => void
  onSave: (config: CamplayerConfig) => Promise<void>
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  config,
  open,
  saving,
  onClose,
  onSave,
}) => {
  const [tab, setTab] = useState<Tab>('cameras')
  const [draft, setDraft] = useState<CamplayerConfig>(config)
  const [error, setError] = useState<string | null>(null)

  // Sync draft when config changes from outside (e.g. SWR refetch)
  React.useEffect(() => {
    setDraft(config)
  }, [config])

  const handleSave = async () => {
    setError(null)
    try {
      await onSave(draft)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    }
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'cameras', label: 'Cameras' },
    { id: 'screens', label: 'Screens' },
    { id: 'advanced', label: 'Advanced' },
  ]

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 bg-black/40 z-30"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <aside
        className={[
          'fixed top-0 right-0 bottom-0 z-40 w-[420px] bg-zinc-950 border-l border-zinc-800 flex flex-col',
          'transition-transform duration-250 ease-in-out',
          open ? 'translate-x-0' : 'translate-x-full',
        ].join(' ')}
        style={{ transitionDuration: '250ms' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 flex-shrink-0">
          <h2 className="text-white font-semibold text-sm">Settings</h2>
          <button onClick={onClose} className="text-zinc-400 hover:text-white transition-colors">
            <X size={16} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-zinc-800 flex-shrink-0">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={[
                'flex-1 py-2 text-xs font-medium transition-colors',
                tab === t.id
                  ? 'text-blue-400 border-b-2 border-blue-500'
                  : 'text-zinc-500 hover:text-zinc-300',
              ].join(' ')}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {tab === 'cameras' && (
            <DeviceEditor
              devices={draft.devices}
              onChange={devices => setDraft(d => ({ ...d, devices }))}
            />
          )}

          {tab === 'screens' && (
            <ScreenEditor
              screens={draft.screens}
              devices={draft.devices}
              onChange={screens => setDraft(d => ({ ...d, screens }))}
            />
          )}

          {tab === 'advanced' && (
            <AdvancedTab
              advanced={draft.advanced}
              onChange={advanced => setDraft(d => ({ ...d, advanced }))}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex-shrink-0 px-4 py-3 border-t border-zinc-800 flex items-center gap-3">
          {error && <span className="text-red-400 text-xs flex-1 truncate">{error}</span>}
          {!error && <span className="flex-1" />}
          <button
            onClick={onClose}
            className="text-xs px-3 py-1.5 text-zinc-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 text-xs px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded transition-colors"
          >
            {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
            Save
          </button>
        </div>
      </aside>
    </>
  )
}

// ─── Advanced settings tab ────────────────────────────────────────────────────

interface AdvancedTabProps {
  advanced: CamplayerConfig['advanced']
  onChange: (a: CamplayerConfig['advanced']) => void
}

function AdvancedTab({ advanced, onChange }: AdvancedTabProps) {
  const set = <K extends keyof CamplayerConfig['advanced']>(
    key: K,
    value: CamplayerConfig['advanced'][K],
  ) => onChange({ ...advanced, [key]: value })

  return (
    <div className="space-y-3 text-sm">
      <Field label="Screen width (0=auto)">
        <NumberInput value={advanced.screen_width} onChange={v => set('screen_width', v)} />
      </Field>
      <Field label="Screen height (0=auto)">
        <NumberInput value={advanced.screen_height} onChange={v => set('screen_height', v)} />
      </Field>
      <Field label="Buffer time (ms)">
        <NumberInput value={advanced.buffertime_ms} onChange={v => set('buffertime_ms', v)} />
      </Field>
      <Field label="Stream watchdog (s)">
        <NumberInput value={advanced.stream_watchdog_sec} onChange={v => set('stream_watchdog_sec', v)} />
      </Field>
      <Field label="Play timeout (s)">
        <NumberInput value={advanced.playtimeout_sec} onChange={v => set('playtimeout_sec', v)} />
      </Field>
      <Field label="Refresh time (min)">
        <NumberInput value={advanced.refreshtime_minutes} onChange={v => set('refreshtime_minutes', v)} />
      </Field>
      <Field label="Stream quality">
        <SelectInput
          value={String(advanced.stream_quality)}
          options={[['0', 'Low'], ['1', 'Auto'], ['2', 'High']]}
          onChange={v => set('stream_quality', parseInt(v) as 0 | 1 | 2)}
        />
      </Field>
      <Field label="HEVC mode">
        <SelectInput
          value={String(advanced.hevc_mode)}
          options={[['0', 'Off'], ['1', 'Auto'], ['2', 'FHD'], ['3', 'UHD']]}
          onChange={v => set('hevc_mode', parseInt(v) as 0 | 1 | 2 | 3)}
        />
      </Field>
      <Field label="Audio mode">
        <SelectInput
          value={String(advanced.audio_mode)}
          options={[['0', 'Off'], ['1', 'Fullscreen']]}
          onChange={v => set('audio_mode', parseInt(v) as 0 | 1)}
        />
      </Field>
      <Field label="Audio volume (%)">
        <NumberInput value={advanced.audio_volume} onChange={v => set('audio_volume', v)} min={0} max={100} />
      </Field>
      <Field label="Screen downscale (%)">
        <NumberInput value={advanced.screen_downscale} onChange={v => set('screen_downscale', v)} min={0} max={100} />
      </Field>
      <Field label="Changeover mode">
        <SelectInput
          value={String(advanced.change_over)}
          options={[['0', 'Normal'], ['1', 'Prebuffer'], ['2', 'Smooth']]}
          onChange={v => set('change_over', parseInt(v) as 0 | 1 | 2)}
        />
      </Field>
      <Field label="Log level">
        <SelectInput
          value={String(advanced.log_level)}
          options={[['0', 'Debug'], ['1', 'Info'], ['2', 'Warn'], ['3', 'Error']]}
          onChange={v => set('log_level', parseInt(v))}
        />
      </Field>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <label className="text-zinc-400 text-xs flex-1">{label}</label>
      <div className="w-32">{children}</div>
    </div>
  )
}

function NumberInput({
  value,
  onChange,
  min,
  max,
}: {
  value: number
  onChange: (v: number) => void
  min?: number
  max?: number
}) {
  return (
    <input
      type="number"
      value={value}
      min={min}
      max={max}
      onChange={e => onChange(parseInt(e.target.value) || 0)}
      className="w-full bg-zinc-800 border border-zinc-700 text-white text-xs px-2 py-1 rounded focus:outline-none focus:border-blue-500 text-right"
    />
  )
}

function SelectInput({
  value,
  options,
  onChange,
}: {
  value: string
  options: [string, string][]
  onChange: (v: string) => void
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="w-full bg-zinc-800 border border-zinc-700 text-white text-xs px-2 py-1 rounded focus:outline-none focus:border-blue-500"
    >
      {options.map(([val, label]) => (
        <option key={val} value={val}>
          {label}
        </option>
      ))}
    </select>
  )
}
