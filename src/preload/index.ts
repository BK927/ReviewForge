import { contextBridge, ipcRenderer } from 'electron'
import { subscribeToProgress } from './progress-subscription'

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
  getTopHelpful: (appId: number, votedUp: boolean, limit?: number) => ipcRenderer.invoke('reviews:top-helpful', appId, votedUp, limit),

  // Analysis
  detectGpu: () => ipcRenderer.invoke('analysis:detect-gpu'),
  runAnalysis: (appId: number, config: Record<string, unknown>) => ipcRenderer.invoke('analysis:run', appId, config),
  getCachedAnalysis: (appId: number) => ipcRenderer.invoke('analysis:get-cached', appId),

  // Export
  exportCsv: (appId: number, filter: Record<string, unknown>) => ipcRenderer.invoke('export:csv', appId, filter),
  exportMarkdown: (appId: number, filter: Record<string, unknown>) => ipcRenderer.invoke('export:markdown', appId, filter),

  // Events
  onProgress: (callback: (data: unknown) => void) => subscribeToProgress(ipcRenderer, callback),

  // Settings
  getSettings: () => ipcRenderer.invoke('settings:get'),
  saveSettings: (settings: Record<string, unknown>) => ipcRenderer.invoke('settings:save', settings)
}

contextBridge.exposeInMainWorld('api', api)

export type ElectronAPI = typeof api
