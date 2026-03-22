import useSWR from 'swr'
import { swrFetcher, putConfig } from '../utils/api'
import type { CamplayerConfig } from '../types/config'

const CONFIG_KEY = '/config'

export interface UseConfigResult {
  config: CamplayerConfig | undefined
  isLoading: boolean
  error: Error | undefined
  saveConfig: (next: CamplayerConfig) => Promise<void>
  mutate: () => void
}

export function useConfig(): UseConfigResult {
  const { data, error, isLoading, mutate } = useSWR<CamplayerConfig>(
    CONFIG_KEY,
    swrFetcher,
    { refreshInterval: 30_000, revalidateOnFocus: false },
  )

  const saveConfig = async (next: CamplayerConfig) => {
    await putConfig(next)
    await mutate()
  }

  return {
    config: data,
    isLoading,
    error: error as Error | undefined,
    saveConfig,
    mutate,
  }
}
