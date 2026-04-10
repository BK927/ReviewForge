const { spawnSync } = require('child_process')

function getNativePrepPlan(target) {
  if (target === 'node') {
    return [
      {
        label: 'better-sqlite3 (node)',
        command: 'npm rebuild better-sqlite3 --verbose'
      }
    ]
  }

  if (target === 'electron') {
    return [
      {
        label: 'electron binary',
        command: 'npm rebuild electron --verbose'
      },
      {
        label: 'better-sqlite3 (electron)',
        command: 'npx electron-builder install-app-deps'
      }
    ]
  }

  throw new Error(`Unknown native runtime target: ${target}`)
}

function runStep(step) {
  console.log(`[native-deps] ${step.label}`)
  const result = spawnSync(step.command, {
    stdio: 'inherit',
    shell: true
  })

  if (result.status !== 0) {
    process.exit(result.status ?? 1)
  }
}

function main() {
  const target = process.argv[2]
  for (const step of getNativePrepPlan(target)) {
    runStep(step)
  }
}

if (require.main === module) {
  main()
}

module.exports = {
  getNativePrepPlan
}
