import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'

interface Props {
  open: boolean
  onClose: () => void
}

interface Settings {
  tier: 'auto' | '0' | '1'
  apiProvider: 'none' | 'claude' | 'openai' | 'gemini'
  apiKey: string
}

export function SettingsDialog({ open, onClose }: Props) {
  const api = useApi()
  const [settings, setSettings] = useState<Settings>({ tier: 'auto', apiProvider: 'none', apiKey: '' })
  const [gpuInfo, setGpuInfo] = useState<any>(null)

  useEffect(() => {
    if (open) {
      api.getSettings().then((s: any) => s && setSettings(s))
      api.detectGpu().then((info: any) => setGpuInfo(info)).catch(() => {})
    }
  }, [open])

  const handleSave = async () => {
    await api.saveSettings(settings as unknown as Record<string, unknown>)
    onClose()
  }

  if (!open) return null

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-dialog" onClick={e => e.stopPropagation()}>
        <h2>Settings</h2>

        <section>
          <h3>Analysis Tier</h3>
          {gpuInfo && (
            <p className="gpu-info">
              GPU: {gpuInfo.gpu_available ? `${gpuInfo.gpu_name} (${gpuInfo.vram_mb}MB VRAM)` : 'Not detected'}
              {gpuInfo.gpu_available && ` — Recommended: Tier ${gpuInfo.recommended_tier}`}
            </p>
          )}
          <select value={settings.tier} onChange={e => setSettings({ ...settings, tier: e.target.value as Settings['tier'] })}>
            <option value="auto">Auto-detect</option>
            <option value="0">Tier 0 — CPU only (multilingual-e5-small)</option>
            <option value="1">Tier 1 — GPU (BGE-M3)</option>
          </select>
        </section>

        <section>
          <h3>LLM API (Optional)</h3>
          <select value={settings.apiProvider} onChange={e => setSettings({ ...settings, apiProvider: e.target.value as Settings['apiProvider'] })}>
            <option value="none">None</option>
            <option value="claude">Claude</option>
            <option value="openai">OpenAI</option>
            <option value="gemini">Gemini</option>
          </select>
          {settings.apiProvider !== 'none' && (
            <input
              type="password"
              placeholder="API Key"
              value={settings.apiKey}
              onChange={e => setSettings({ ...settings, apiKey: e.target.value })}
            />
          )}
        </section>

        <div className="dialog-actions">
          <button onClick={onClose}>Cancel</button>
          <button onClick={handleSave} className="primary">Save</button>
        </div>
      </div>
    </div>
  )
}
