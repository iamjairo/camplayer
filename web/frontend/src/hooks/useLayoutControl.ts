import { useCallback } from 'react'
import { postNextScreen, postPrevScreen, postSetScreen } from '../utils/api'

export interface UseLayoutControlResult {
  nextScreen: (displayIdx?: number) => Promise<void>
  prevScreen: (displayIdx?: number) => Promise<void>
  setScreen: (screenIdx: number, displayIdx?: number) => Promise<void>
}

export function useLayoutControl(): UseLayoutControlResult {
  const nextScreen = useCallback(
    (displayIdx = 0) => postNextScreen(displayIdx),
    [],
  )

  const prevScreen = useCallback(
    (displayIdx = 0) => postPrevScreen(displayIdx),
    [],
  )

  const setScreen = useCallback(
    (screenIdx: number, displayIdx = 0) => postSetScreen(displayIdx, screenIdx),
    [],
  )

  return { nextScreen, prevScreen, setScreen }
}
