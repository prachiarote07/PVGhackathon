import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, join } from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const windows = process.platform === 'win32';
// Fixed command and arguments; no user input is interpolated into a shell string.
const result = windows
  ? spawnSync('cmd.exe', ['/d', '/s', '/c', 'gradlew.bat assembleDebug --no-daemon'], { cwd: join(root, 'android'), stdio: 'inherit', windowsHide: true })
  : spawnSync('sh', ['./gradlew', 'assembleDebug', '--no-daemon'], { cwd: join(root, 'android'), stdio: 'inherit' });
if (result.error || result.status !== 0) {
  console.error('Android compilation did not succeed. No new APK is verified.', result.error?.message || '');
  process.exitCode = result.status || 1;
} else {
  const apk = join(root, 'android', 'app', 'build', 'outputs', 'apk', 'debug', 'app-debug.apk');
  if (!existsSync(apk)) { console.error('Gradle ended without an APK at the expected path.'); process.exitCode = 1; }
  else console.log(`Debug APK built: ${apk}\nInstall with: adb install -r "${apk}"`);
}
