/** Build-time vendoring: no runtime CDN dependencies, no paid service or API key. */
import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, readdirSync, copyFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';

const version = '6.10.0';
const temporary = mkdtempSync(join(tmpdir(), 'commons-maplibre-'));
const destination = `public/vendor/maplibre-${version}`;
try {
  const [metadata] = JSON.parse(execFileSync('npm', ['pack', `maplibre-gl@${version}`, '--ignore-scripts', '--json', '--pack-destination', temporary], { encoding: 'utf8' }));
  if (!metadata?.filename || metadata.name !== 'maplibre-gl' || metadata.version !== version) throw new Error('Unexpected MapLibre package.');
  execFileSync('tar', ['-xzf', join(temporary, metadata.filename), '-C', temporary]);
  const packagePath = join(temporary, 'package');
  const pkg = JSON.parse(readFileSync(join(packagePath, 'package.json'), 'utf8'));
  if (pkg.name !== 'maplibre-gl' || pkg.version !== version) throw new Error('Package metadata mismatch.');
  const dist = join(packagePath, 'dist');
  const files = readdirSync(dist).filter(name => /\.(mjs|css)$/.test(name));
  for (const required of ['maplibre-gl.mjs', 'maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs', 'maplibre-gl.css']) {
    if (!files.includes(required)) throw new Error(`Missing required runtime file: ${required}`);
  }
  mkdirSync(destination, { recursive: true });
  const hashes = {};
  for (const file of files) {
    const bytes = readFileSync(join(dist, file));
    copyFileSync(join(dist, file), join(destination, file));
    hashes[file] = createHash('sha256').update(bytes).digest('hex');
  }
  const licenses = readdirSync(packagePath).filter(name => /^(LICENSE|NOTICE)/i.test(name));
  if (!licenses.length) throw new Error('MapLibre license is missing.');
  for (const file of licenses) copyFileSync(join(packagePath, file), join(destination, file));
  writeFileSync(join(destination, 'manifest.json'), JSON.stringify({ package: pkg.name, version, integrity: metadata.integrity, sha256: hashes }, null, 2) + '\n');
  console.log(`Vendored MapLibre ${version}: ${files.join(', ')}`);
} finally {
  rmSync(temporary, { recursive: true, force: true });
}
