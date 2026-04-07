import { contextBridge, ipcRenderer } from 'electron'

const api = {
  // Games
  addGame: (input: string) => ipcRenderer.invoke('game:add', input),
  getGames: () => ipcRenderer.invoke('game:list'),
  getGame: (appId: number) => ipcRenderer.invoke('game:get', appId),
  deleteGame: (appId: number) => ipcRenderer.invoke('game:delete', appId),
  getGameStats: (appId: number) => ipcRenderer.invoke('game:stats', appId),

  // Reviews
  fetchReviews: (appId: number) => ipcRenderer.invoke('reviews:fetch', appId),
  getReviews: (appId: number, filter?: Record<string, unknown>) => ipcRenderer.invoke('reviews:get', appId, filter),

  // Analysis
  detectGpu: () => ipcRenderer.invoke('analysis:detect-gpu'),
  runAnalysis: (appId: number, config: Record<string, unknown>) => ipcRenderer.invoke('analysis:run', appId, config),

  // Export
  exportCsv: (appId: number, filter: Record<string, unknown>) => ipcRenderer.invoke('export:csv', appId, filter),
  exportMarkdown: (appId: number, filter: Record<string, unknown>) => ipcRenderer.invoke('export:markdown', appId, filter),

  // Events
  onProgress: (callback: (data: unknown) => void) => {
    ipcRenderer.on('progress', (_event, data) => callback(data))
    return () => ipcRenderer.removeAllListeners('progress')
  },

  // Settings
  getSettings: () => ipcRenderer.invoke('settings:get'),
  saveSettings: (settings: Record<string, unknown>) => ipcRenderer.invoke('settings:save', settings)
}

contextBridge.exposeInMainWorld('api', api)

export type ElectronAPI = typeof api
