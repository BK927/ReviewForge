import { describe, it, expect, vi } from 'vitest'
import { subscribeToProgress } from '../../src/preload/progress-subscription'

type ProgressListener = (_event: unknown, data: unknown) => void

function createFakeIpcRenderer() {
  const listeners = new Set<ProgressListener>()

  return {
    on: (_channel: string, listener: ProgressListener) => {
      listeners.add(listener)
    },
    off: (_channel: string, listener: ProgressListener) => {
      listeners.delete(listener)
    },
    emit: (data: unknown) => {
      for (const listener of listeners) {
        listener({}, data)
      }
    },
    listenerCount: () => listeners.size
  }
}

describe('subscribeToProgress', () => {
  it('removes only its own progress listener during cleanup', () => {
    const ipcRenderer = createFakeIpcRenderer()
    const first = vi.fn()
    const second = vi.fn()

    const cleanupFirst = subscribeToProgress(ipcRenderer, first)
    subscribeToProgress(ipcRenderer, second)

    expect(ipcRenderer.listenerCount()).toBe(2)

    ipcRenderer.emit({ type: 'analysis' })
    expect(first).toHaveBeenCalledTimes(1)
    expect(second).toHaveBeenCalledTimes(1)

    cleanupFirst()
    expect(ipcRenderer.listenerCount()).toBe(1)

    ipcRenderer.emit({ type: 'fetch' })
    expect(first).toHaveBeenCalledTimes(1)
    expect(second).toHaveBeenCalledTimes(2)
  })

  it('falls back to removeListener when off is unavailable', () => {
    const listeners = new Set<ProgressListener>()
    const ipcRenderer = {
      on: (_channel: string, listener: ProgressListener) => {
        listeners.add(listener)
      },
      removeListener: (_channel: string, listener: ProgressListener) => {
        listeners.delete(listener)
      }
    }

    const callback = vi.fn()
    const cleanup = subscribeToProgress(ipcRenderer, callback)

    expect(listeners.size).toBe(1)
    cleanup()
    expect(listeners.size).toBe(0)
  })
})
