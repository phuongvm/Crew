// Runs the unit tests under ui/src/**/__tests__/*.test.tsx: each is bundled with esbuild (the Desktop SDK, which only the
// host provides, is replaced by an empty module) and executed by node. Exit 1 when any test throws.
//   node ui/test.mjs
import { build } from 'esbuild'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const UI = path.dirname(fileURLToPath(import.meta.url))
const walk = d => fs.readdirSync(d, { withFileTypes: true }).flatMap(e =>
  e.isDirectory() ? walk(path.join(d, e.name)) : e.name.endsWith('.test.tsx') ? [path.join(d, e.name)] : [])
const tests = walk(path.join(UI, 'src'))
const out = fs.mkdtempSync(path.join(process.env.TMPDIR || os.tmpdir(), 'crew-ui-test-'))
const stubSdk = {
  name: 'stub-sdk',
  setup(b) {
    b.onResolve({ filter: /^@hermes\/plugin-sdk$/ }, () => ({ path: 'sdk', namespace: 'stub-sdk' }))
    b.onLoad({ filter: /.*/, namespace: 'stub-sdk' }, () => ({ contents: 'export const Codicon = undefined', loader: 'js' }))
  }
}
let failed = 0
try {
  for (const file of tests) {
    const outfile = path.join(out, path.basename(file) + '.mjs')
    await build({ entryPoints: [file], outfile, bundle: true, format: 'esm', platform: 'node', jsx: 'automatic', jsxImportSource: 'react',
      loader: { '.css': 'text', '.woff2': 'dataurl' }, plugins: [stubSdk], absWorkingDir: UI, logLevel: 'warning',
      define: { 'process.env.NODE_ENV': '"test"', __CREW_VERSION__: '"test"' } })
    const r = spawnSync(process.execPath, [outfile], { encoding: 'utf8' })
    process.stdout.write(`${path.relative(UI, file)}: ${r.stdout}${r.stderr}`)
    if (r.status !== 0) failed++
  }
} finally {
  fs.rmSync(out, { recursive: true, force: true })
}
if (!tests.length) { console.error('FAILED: no *.test.tsx found'); process.exit(1) }
process.exit(failed ? 1 : 0)
