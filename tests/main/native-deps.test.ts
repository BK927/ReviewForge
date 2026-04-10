import { describe, expect, it } from 'vitest'
import pkg from '../../package.json'
import { getNativePrepPlan } from '../../scripts/prepare-native-deps'

describe('getNativePrepPlan', () => {
  it('returns the node runtime rebuild steps for test runs', () => {
    expect(getNativePrepPlan('node')).toEqual([
      {
        label: 'better-sqlite3 (node)',
        command: 'npm rebuild better-sqlite3 --verbose'
      }
    ])
  })

  it('returns the electron runtime rebuild steps for app runs', () => {
    expect(getNativePrepPlan('electron')).toEqual([
      {
        label: 'electron binary',
        command: 'npm rebuild electron --verbose'
      },
      {
        label: 'better-sqlite3 (electron)',
        command: 'npx electron-builder install-app-deps'
      }
    ])
  })
})

describe('native dependency scripts', () => {
  it('routes test runs through the node rebuild helper', () => {
    expect(pkg.scripts.test).toBe('node scripts/prepare-native-deps.js node && vitest run')
  })

  it('routes electron-facing commands through the electron rebuild helper', () => {
    expect(pkg.scripts.postinstall).toBe('node scripts/prepare-native-deps.js electron')
    expect(pkg.scripts.dev).toBe('node scripts/prepare-native-deps.js electron && electron-vite dev')
    expect(pkg.scripts.start).toBe('node scripts/prepare-native-deps.js electron && electron-vite preview')
    expect(pkg.scripts.build).toBe('node scripts/prepare-native-deps.js electron && pnpm typecheck && electron-vite build')
  })
})
