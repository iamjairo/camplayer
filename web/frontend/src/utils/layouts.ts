import type { LayoutId } from '../types/config'

export type { LayoutId }

export interface LayoutDefinition {
  id: LayoutId
  name: string
  windowCount: number
  cols: number
  rows: number
  /** CSS grid-template-areas string. Each cell token is "w1", "w2", etc. */
  areas: string
  /** 1-based window indices that span more than one grid cell */
  largeWindows: number[]
}

export const LAYOUTS: Record<LayoutId, LayoutDefinition> = {
  // ─── Simple uniform grids ─────────────────────────────────────────────────
  1: {
    id: 1, name: '1×1', windowCount: 1, cols: 1, rows: 1, largeWindows: [],
    areas: '"w1"',
  },
  4: {
    id: 4, name: '2×2', windowCount: 4, cols: 2, rows: 2, largeWindows: [],
    areas: '"w1 w2" "w3 w4"',
  },
  9: {
    id: 9, name: '3×3', windowCount: 9, cols: 3, rows: 3, largeWindows: [],
    areas: '"w1 w2 w3" "w4 w5 w6" "w7 w8 w9"',
  },
  16: {
    id: 16, name: '4×4', windowCount: 16, cols: 4, rows: 4, largeWindows: [],
    areas: '"w1 w2 w3 w4" "w5 w6 w7 w8" "w9 w10 w11 w12" "w13 w14 w15 w16"',
  },

  // ─── 1+5: 3×3 grid, w1 spans 2×2 top-left, w2-w6 fill remaining 5 cells ──
  6: {
    id: 6, name: '1+5', windowCount: 6, cols: 3, rows: 3, largeWindows: [1],
    areas: '"w1 w1 w2" "w1 w1 w3" "w4 w5 w6"',
  },

  // ─── 1+7: 4×3 grid, w1 spans 2×2 top-left, w2-w8 fill remaining 8 cells ─
  //   Row1: w1 w1 w2 w3
  //   Row2: w1 w1 w4 w5
  //   Row3: w6 w7 w8 .
  8: {
    id: 8, name: '1+7', windowCount: 8, cols: 4, rows: 3, largeWindows: [1],
    areas: '"w1 w1 w2 w3" "w1 w1 w4 w5" "w6 w7 w8 ."',
  },

  // ─── 3+4: 4×2 grid, w1 spans 2 rows col1, w2/w3 each 1 row col2,
  //         w4-w7 are small in cols 3-4
  //   Row1: w1 w2 w4 w5
  //   Row2: w1 w3 w6 w7
  7: {
    id: 7, name: '3+4', windowCount: 7, cols: 4, rows: 2, largeWindows: [1, 2, 3],
    areas: '"w1 w2 w4 w5" "w1 w3 w6 w7"',
  },

  // ─── 2+8: 4×4 grid, w1 spans 2×2 rows 1-2, w2 spans 2×2 rows 3-4,
  //         w3-w10 are small in cols 3-4
  //   Row1: w1 w1 w3  w4
  //   Row2: w1 w1 w5  w6
  //   Row3: w2 w2 w7  w8
  //   Row4: w2 w2 w9  w10
  10: {
    id: 10, name: '2+8', windowCount: 10, cols: 4, rows: 4, largeWindows: [1, 2],
    areas: '"w1 w1 w3 w4" "w1 w1 w5 w6" "w2 w2 w7 w8" "w2 w2 w9 w10"',
  },

  // ─── 1+12: 4×4 grid, w1 spans 2×2 top-left, w2-w13 fill remaining 12 ────
  //   Row1: w1  w1  w2  w3
  //   Row2: w1  w1  w4  w5
  //   Row3: w6  w7  w8  w9
  //   Row4: w10 w11 w12 w13
  13: {
    id: 13, name: '1+12', windowCount: 13, cols: 4, rows: 4, largeWindows: [1],
    areas: '"w1 w1 w2 w3" "w1 w1 w4 w5" "w6 w7 w8 w9" "w10 w11 w12 w13"',
  },
}

export const LAYOUT_IDS: LayoutId[] = [1, 4, 9, 16, 6, 8, 7, 10, 13]

export function getLayout(id: number): LayoutDefinition {
  return LAYOUTS[id as LayoutId] ?? LAYOUTS[1]
}
