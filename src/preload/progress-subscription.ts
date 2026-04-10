type ProgressListener = (_event: unknown, data: unknown) => void

interface ProgressEmitter {
  on: (channel: string, listener: ProgressListener) => void
  off?: (channel: string, listener: ProgressListener) => void
  removeListener?: (channel: string, listener: ProgressListener) => void
}

export function subscribeToProgress(ipcRenderer: ProgressEmitter, callback: (data: unknown) => void): () => void {
  const listener: ProgressListener = (_event, data) => callback(data)

  ipcRenderer.on('progress', listener)

  return () => {
    if (typeof ipcRenderer.off === 'function') {
      ipcRenderer.off('progress', listener)
      return
    }

    ipcRenderer.removeListener?.('progress', listener)
  }
}
