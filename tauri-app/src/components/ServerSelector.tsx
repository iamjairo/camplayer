import { useState } from 'react'
import { Wifi, RefreshCw, Server, Plus, CheckCircle, XCircle } from 'lucide-react'
import { useServerDiscovery } from '../hooks/useServerDiscovery'
import { useServerHistory } from '../hooks/useServerHistory'
import { testConnection } from '../utils/tauri-bridge'
import type { ServerInfo } from '../utils/types'

interface Props {
  onConnect: (server: ServerInfo) => void
}

export function ServerSelector({ onConnect }: Props) {
  const { servers: discovered, scanning, rescan } = useServerDiscovery()
  const { history, addServer } = useServerHistory()
  const [manualHost, setManualHost] = useState('')
  const [manualPort, setManualPort] = useState('80')
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<boolean | null>(null)

  const handleConnect = async (server: ServerInfo) => {
    await addServer({ ...server, last_connected: new Date().toISOString() })
    onConnect(server)
  }

  const handleTest = async () => {
    setTesting(true)
    const url = `http://${manualHost}:${manualPort}`
    const ok = await testConnection(url)
    setTestResult(ok)
    setTesting(false)
  }

  const handleManualConnect = async () => {
    const server: ServerInfo = {
      name: `Camplayer @ ${manualHost}`,
      host: manualHost,
      port: parseInt(manualPort),
      api_url: `http://${manualHost}:${manualPort}`,
      discovered: false,
      last_connected: new Date().toISOString(),
    }
    await handleConnect(server)
  }

  return (
    <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-lg">
        <div className="flex items-center gap-3 mb-8">
          <Server className="text-blue-400" size={32} />
          <div>
            <h1 className="text-2xl font-bold">Camplayer</h1>
            <p className="text-zinc-400 text-sm">Connect to a Camplayer server</p>
          </div>
        </div>

        {/* Discovered */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
              Discovered
            </h2>
            <button
              onClick={rescan}
              disabled={scanning}
              className="text-blue-400 hover:text-blue-300 flex items-center gap-1 text-xs"
            >
              <RefreshCw size={12} className={scanning ? 'animate-spin' : ''} />
              {scanning ? 'Scanning...' : 'Rescan'}
            </button>
          </div>
          {discovered.map((s) => (
            <button
              key={`${s.host}:${s.port}`}
              onClick={() => handleConnect(s)}
              className="w-full flex items-center gap-3 p-3 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 rounded-lg mb-2 text-left transition-colors"
            >
              <Wifi size={16} className="text-green-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{s.name}</div>
                <div className="text-xs text-zinc-500">{s.api_url}</div>
              </div>
            </button>
          ))}
          {discovered.length === 0 && !scanning && (
            <p className="text-zinc-600 text-sm py-2">No servers found on local network</p>
          )}
        </div>

        {/* History */}
        {history.length > 0 && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-2">
              Recent
            </h2>
            {history.map((s) => (
              <button
                key={`${s.host}:${s.port}`}
                onClick={() => handleConnect(s)}
                className="w-full flex items-center gap-3 p-3 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-lg mb-2 text-left transition-colors"
              >
                <Server size={16} className="text-zinc-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{s.name}</div>
                  <div className="text-xs text-zinc-500">{s.api_url}</div>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Manual entry */}
        <div>
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-2">
            Manual
          </h2>
          <div className="flex gap-2">
            <input
              value={manualHost}
              onChange={(e) => setManualHost(e.target.value)}
              placeholder="192.168.1.100 or hostname"
              className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm focus:border-blue-500 outline-none"
            />
            <input
              value={manualPort}
              onChange={(e) => setManualPort(e.target.value)}
              placeholder="80"
              className="w-20 bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm focus:border-blue-500 outline-none"
            />
          </div>
          <div className="flex gap-2 mt-2">
            <button
              onClick={handleTest}
              disabled={!manualHost || testing}
              className="flex items-center gap-1 px-3 py-2 bg-zinc-800 hover:bg-zinc-700 rounded text-sm disabled:opacity-50"
            >
              {testResult === true ? (
                <CheckCircle size={14} className="text-green-400" />
              ) : testResult === false ? (
                <XCircle size={14} className="text-red-400" />
              ) : (
                <Plus size={14} />
              )}
              Test
            </button>
            <button
              onClick={handleManualConnect}
              disabled={!manualHost}
              className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium disabled:opacity-50"
            >
              Connect
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
