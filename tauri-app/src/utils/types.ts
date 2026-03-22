export interface ServerInfo {
  name: string
  host: string
  port: number
  api_url: string
  discovered: boolean
  last_connected: string | null
}
