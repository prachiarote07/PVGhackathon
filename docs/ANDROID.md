# MoneyFy Android — build and device guide

## Current state

The existing React/Vite frontend is wrapped with **Capacitor 8.5.3**, not rewritten. The native Android project is `frontend/android/`, app label **MoneyFy**, application ID `com.moneyfy.app`, tagline **Your Moves, Made Smarter.** The package ID is a local hackathon default; review its uniqueness before public store distribution.

The rotating coin, nine pages and all eleven planned financial capabilities remain available at their previous implementation level. Offline demo calculations run inside the WebView. Signed-in accounts now use FastAPI, SQL persistence and Python analytics. SQLite persistence is verified; PostgreSQL is configured but not executed locally.

**This laptop cannot currently compile the APK.** The latest check on 10 October 2026 detected Node 24.21.0, selected Java 26, Android Studio, SDK Build-Tools 36.0.0 and platform-tools/adb. SDK Platform 36 is still missing and JDK 21 must be selected (JAVA_HOME is unset). No APK has been generated; emulator and physical-device execution remain unverified.

## Install prerequisites

1. Install Android Studio Otter 2025.2.1 or newer, or the equivalent standalone SDK toolchain. Use **JDK 21** for this project. The bundled Gradle 8.14.3 does not run on Java 26; Java 17 cannot compile Capacitor's Java 21 sources. Set `JAVA_HOME` to the actual JDK 21 location, not the Oracle `javapath` shim.
2. In Android Studio → SDK Manager install **Android SDK Platform 36**, **Android SDK Build-Tools 35.0.0** (AGP 8.13 default), **Android SDK Platform-Tools**, and **Android SDK Command-line Tools (latest)**. Install an emulator/system image if you intend to test without a phone. Minimum app Android version is API 24 (Android 7.0).
3. Set `ANDROID_HOME` to the actual SDK directory and accept SDK licenses. `ANDROID_SDK_ROOT`, if set, must point to the same SDK. Alternatively, Android Studio can create the ignored `frontend/android/local.properties` containing `sdk.dir`.
4. A first native build needs network access to download Gradle and Maven dependencies. SDK license acceptance is a prerequisite, not something this app bypasses.

Example PowerShell **session** setup (replace the JDK path with the installed JDK 21 location):

```powershell
$env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-21'
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$env:Path = "$env:JAVA_HOME\bin;$env:ANDROID_HOME\platform-tools;$env:Path"
& "$env:ANDROID_HOME\cmdline-tools\latest\bin\sdkmanager.bat" --licenses
```

If using the command-line SDK Manager, package installation is:

```powershell
& "$env:ANDROID_HOME\cmdline-tools\latest\bin\sdkmanager.bat" 'platforms;android-36' 'build-tools;35.0.0' 'platform-tools'
```

## Build an installable debug APK

From the repository root:

```powershell
cd frontend
npm ci
npm run android:doctor
npm run android:apk
```

The APK script checks prerequisites, builds Vite in Android mode, syncs the packaged assets and plugins, then runs `assembleDebug`. A successful build places the debug-signed installable APK at:

```text
frontend/android/app/build/outputs/apk/debug/app-debug.apk
```

That is an **expected output path**, not an existing deliverable at this checkpoint. Debug builds are for the team demo. Public distribution needs a reviewed release configuration, a privately held signing key and the relevant store requirements. Signing keys and APKs are ignored by Git; never commit signing passwords.

To use Android Studio instead:

```powershell
npm run android:sync
npm run android:open
```

Let Gradle sync, select JDK 21 in Gradle settings, then use Build → Generate App Bundles or APKs → Build APK(s). Menu wording may vary by Studio version. The checked-in Gradle wrapper means a global Gradle installation is unnecessary.

## Install and run

Enable developer options and USB debugging on your test phone, connect it, and approve that computer on the device. Then from `frontend/`:

```powershell
adb devices
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.moneyfy.app/.MainActivity
```

Alternatively, `npm run android:run` syncs then uses Capacitor's device selection/build workflow. You can also transfer the debug APK and approve installation from that source in Android Settings. No device installation was performed during this task.

## Backend URLs: phone, emulator and web

`frontend/.env.example` is the template. Copy it to `frontend/.env.android.local` for Android. Leaving `VITE_API_BASE_URL` empty intentionally builds the **offline demo**; there is no fabricated live endpoint. Example for the reachable deployed backend:

```dotenv
VITE_API_BASE_URL=https://YOUR-ACTUAL-API-HOST/api/v1
```

Re-run `npm run android:sync` and rebuild the APK after changing this value. It is a build-time public setting, not a secret. The website uses `frontend/.env.local`; explicit Android values override common environment files, while shell environment variables take precedence.

| Where the app runs | How to reach the laptop backend |
| --- | --- |
| Browser on the same laptop, Vite development only | `http://127.0.0.1:8000/api/v1` is allowed for local development |
| Android emulator | The emulator's host alias is `10.0.2.2`. This app still requires HTTPS with a trusted certificate matching the host; a public trusted HTTPS development endpoint is usually easier. `https://10.0.2.2:8443/api/v1` alone does not make an untrusted certificate valid. |
| Physical Android phone | Use a reachable trusted HTTPS host, such as a deployed backend or a deliberately configured development HTTPS proxy. A laptop LAN address works only with matching trusted TLS and network reachability. |
| Production website and APK | Use the team's deployed HTTPS API |

**Never use phone/emulator `localhost` as the laptop API address.** `https://localhost` in `capacitor.config.json` is different: it is Capacitor's internal origin for bundled HTML/JavaScript, not the API server. No `server.url`, live-reload dependency or remote website wrapper is configured.

With an HTTPS API configured, signup/login opens database-backed financial pages using Python analysis. The offline demo remains separate. Privacy Center in demo mode also offers an optional health-only check; account request failures never silently substitute demo data.

## HTTPS, permissions and backend CORS

- Android declares only `INTERNET` in the application manifest. The system document picker supplies selected CSV files; no broad storage, contacts, SMS, location or camera permission is requested.
- Both manifest/network security policy and Capacitor disable cleartext traffic and mixed content. System certificate trust is retained. There is no permissive SSL handler or trust-all bypass.
- Android builds reject API credentials in URLs, HTTP and loopback API addresses. Web builds permit HTTP only for a loopback development server.
- Packaged HTML includes a content security policy allowing connections only to its own origin and the configured API origin. Financial data is not embedded into the URL or diagnostics.
- Fetch uses a timeout, rejects redirects, excludes browser credentials, and reports non-JSON/error responses explicitly. Account requests include an expiring bearer token; the API enforces ownership. Production authentication hardening and deployment review remain necessary before personal banking use.
- Android backup and device-transfer exclusions are configured for local demo data. Local WebView storage is not encrypted by this application.

FastAPI uses an explicit CORS allowlist; configure CORS_ORIGINS for deployed client origins. The Android origin is **`https://localhost`**. The local Vite website uses **`http://127.0.0.1:5173`** (and `http://localhost:5173` only if used). Add the deployed website origin as appropriate. Permit required methods and headers, including OPTIONS/preflights. This implementation sends no cookie credentials; do not use wildcard credentials. HTTPS does not remove the need for CORS. For local-device testing, bind the server to a reachable interface and configure the firewall/proxy deliberately.

## Mobile behavior and retained fallback

- Bottom navigation gives thumb-friendly access to Overview, Autopilot, What-if, Goals and all other pages through More.
- Safe-area padding uses Capacitor SystemBars insets and CSS environment fallbacks. The software keyboard uses resize behavior; pages/dialogs can scroll.
- Touch pointers tap charts to pin exact values; desktop pointers hover. Tables provide a second accessible way to inspect each date and balance. Range controls have larger touch areas; forms use appropriate numeric/date inputs.
- Android Back closes a modal, then an open menu, then navigates history (or Home for a direct entry); Back at Home minimizes the app. This native plugin behavior still requires device verification.
- Export uses the Android share/save sheet from an app-private cache file. Web exports remain normal downloads. Cache exports are cleared on next launch and local-data deletion/reset; copies users save/share outside the app are not deleted by MoneyFy. No export leaves the app until the user chooses a destination.
- CSV uses the native WebView/system file picker. Excel remains planned, as before.

The original website still runs with `npm run dev`, builds to `dist/` with `npm run build`, and previews with `npm run preview`. Android builds use **`dist-android/`**, so neither output overwrites the other.

## Verification commands

```powershell
npm test
npm run build
npm run android:sync
npm run test:e2e
npm run test:android-web
npm run android:doctor
```

`test:android-web` serves the actual packaged web build in touch-enabled Chrome, including its content security policy. It is **not** an Android emulator or native plugin test. After the SDK is available, check installation, cold launch/coin, rotation, Back, keyboard, CSV picker, native export, chart taps, scenario dragging, consent, delete/reset, process restart persistence, airplane-mode demo and real HTTPS health check on a physical device.

The pending native `MoneyFyShellTest` verifies package identity, app name, cleartext blocking and backup flag on a device. Run `./gradlew.bat connectedDebugAndroidTest` from `frontend/android/` after SDK setup and device connection. See `ANDROID_DEVICE_CHECKLIST.md` for the manual flows that this small instrumentation test does not cover.

## Sources and team review

Configuration follows the official [Capacitor configuration guide](https://capacitorjs.com/docs/config), [Android requirements](https://capacitorjs.com/docs/updating/8-0), [SystemBars safe-area guidance](https://capacitorjs.com/docs/apis/system-bars), [App back-button API](https://capacitorjs.com/docs/apis/app), [Filesystem](https://capacitorjs.com/docs/apis/filesystem), [Share](https://capacitorjs.com/docs/apis/share), and [Gradle Java compatibility](https://docs.gradle.org/current/userguide/compatibility.html). Installed Capacitor templates provide SDK 36, AGP 8.13.0, Gradle 8.14.3 and Java 21 source compatibility.

Yadnesha reviews frontend and native-shell changes; Prachi reviews API configuration/CORS integration; Mansi reviews device checks. Commit ownership of shared docs remains to be agreed. No commit, push, signing identity change or deployment has been performed.
