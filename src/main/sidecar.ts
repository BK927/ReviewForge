import { spawn, ChildProcess } from 'child_process'
import { randomUUID } from 'crypto'
import path from 'path'
import { app } from 'electron'

interface PendingRequest {
  resolve: (data: unknown) => void
  reject: (error: Error) => void
  onProgress?: (data: { percent: number; message: string }) => void
}

export class SidecarManager {
  private process: ChildProcess | null = null
  private pending = new Map<string, PendingRequest>()
  private buffer = ''
  private ready = false
  private readyPromise: Promise<void> | null = null

  start(): Promise<void> {
    if (this.readyPromise) return this.readyPromise

    this.readyPromise = new Promise((resolve, reject) => {
      const pythonPath = this.getPythonPath()
      const scriptPath = this.getScriptPath()

      this.process = spawn(pythonPath, [scriptPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
        cwd: path.dirname(scriptPath),
        env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
      })

      this.process.stdout!.on('data', (chunk: Buffer) => {
        this.buffer += chunk.toString()
        const lines = this.buffer.split('\n')
        this.buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.trim()) continue
          try {
            const msg = JSON.parse(line)
            this.handleMessage(msg)
            if (msg.id === '__init__' && msg.data?.status === 'ready') {
              this.ready = true
              resolve()
            }
          } catch {
            console.error('Sidecar: invalid JSON from Python:', line)
          }
        }
      })

      this.process.stderr!.on('data', (chunk: Buffer) => {
        console.error('Sidecar stderr:', chunk.toString())
      })

      this.process.on('exit', (code) => {
        this.ready = false
        this.process = null
        this.readyPromise = null
        // Reject all pending requests when sidecar crashes
        for (const [, req] of this.pending) {
          req.reject(new Error(`Sidecar exited unexpectedly (code ${code})`))
        }
        this.pending.clear()
        reject(new Error(`Sidecar exited with code ${code}`))
      })

      setTimeout(() => {
        if (!this.ready) reject(new Error('Sidecar startup timeout'))
      }, 30000)
    })

    return this.readyPromise
  }

  async send(method: string, params: Record<string, unknown> = {}, onProgress?: (data: { percent: number; message: string }) => void): Promise<unknown> {
    if (!this.process || !this.ready) {
      await this.start()
    }

    const id = randomUUID()
    const message = JSON.stringify({ id, method, params }) + '\n'

    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject, onProgress })
      this.process!.stdin!.write(message)
    })
  }

  stop(): void {
    if (this.process) {
      this.process.kill()
      this.process = null
      this.ready = false
      this.readyPromise = null
    }
  }

  private handleMessage(msg: { id: string; type: string; data: unknown }): void {
    const pending = this.pending.get(msg.id)
    if (!pending) return

    if (msg.type === 'result') {
      this.pending.delete(msg.id)
      pending.resolve(msg.data)
    } else if (msg.type === 'error') {
      this.pending.delete(msg.id)
      pending.reject(new Error((msg.data as { message: string }).message))
    } else if (msg.type === 'progress') {
      pending.onProgress?.(msg.data as { percent: number; message: string })
    }
  }

  private getPythonPath(): string {
    const isWin = process.platform === 'win32'
    const venvBin = isWin ? 'Scripts/python.exe' : 'bin/python'
    if (app.isPackaged) {
      return path.join(process.resourcesPath, 'python', 'venv', venvBin)
    }
    return path.join(__dirname, '..', '..', 'python', '.venv', venvBin)
  }

  private getScriptPath(): string {
    if (app.isPackaged) {
      return path.join(process.resourcesPath, 'python', 'main.py')
    }
    return path.join(__dirname, '..', '..', 'python', 'main.py')
  }
}
