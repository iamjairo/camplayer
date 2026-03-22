import React from 'react'
import { LAYOUT_IDS, LAYOUTS } from '../utils/layouts'
import type { LayoutId } from '../utils/layouts'

interface LayoutPickerProps {
  value: LayoutId
  onChange: (id: LayoutId) => void
}

/** Renders a tiny SVG thumbnail representing the grid layout. */
function LayoutThumbnail({ areas, cols, rows }: { areas: string; cols: number; rows: number }) {
  const cellW = 40 / cols
  const cellH = 30 / rows

  // Parse grid-template-areas into a 2D array of cell names
  const rowStrings = areas.replace(/"/g, '').trim().split('"').filter(Boolean).map(s => s.trim())
  const parsed: string[][] = rowStrings.map(row => row.split(/\s+/))

  // Build a map of name → set of {col,row} positions
  const drawn = new Set<string>()
  const rects: { x: number; y: number; w: number; h: number; name: string }[] = []

  for (let r = 0; r < parsed.length; r++) {
    for (let c = 0; c < (parsed[r]?.length ?? 0); c++) {
      const name = parsed[r][c]
      if (!name || name === '.' || drawn.has(name)) continue
      drawn.add(name)
      // Find span
      let spanC = 1
      let spanR = 1
      while (c + spanC < (parsed[r]?.length ?? 0) && parsed[r][c + spanC] === name) spanC++
      while (r + spanR < parsed.length && parsed[r + spanR]?.[c] === name) spanR++
      rects.push({ x: c * cellW, y: r * cellH, w: spanC * cellW, h: spanR * cellH, name })
    }
  }

  const isLarge = (name: string) => {
    const r = rects.find(r => r.name === name)
    return r && (r.w > cellW || r.h > cellH)
  }

  return (
    <svg viewBox="0 0 40 30" className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
      <rect width="40" height="30" fill="#111" rx="1" />
      {rects.map(rect => (
        <rect
          key={rect.name}
          x={rect.x + 0.5}
          y={rect.y + 0.5}
          width={rect.w - 1}
          height={rect.h - 1}
          fill={isLarge(rect.name) ? '#1d4ed8' : '#27272a'}
          rx="0.5"
        />
      ))}
    </svg>
  )
}

export const LayoutPicker: React.FC<LayoutPickerProps> = ({ value, onChange }) => {
  return (
    <div className="grid grid-cols-3 gap-2">
      {LAYOUT_IDS.map(id => {
        const def = LAYOUTS[id]
        const active = id === value
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            className={[
              'flex flex-col items-center gap-1 p-1.5 rounded border transition-colors',
              active
                ? 'border-blue-500 bg-blue-950/30'
                : 'border-zinc-700 hover:border-zinc-500 bg-zinc-900',
            ].join(' ')}
            title={def.name}
          >
            <div className="w-10 h-[30px]">
              <LayoutThumbnail areas={def.areas} cols={def.cols} rows={def.rows} />
            </div>
            <span className="text-xs text-zinc-400">{def.name}</span>
          </button>
        )
      })}
    </div>
  )
}
