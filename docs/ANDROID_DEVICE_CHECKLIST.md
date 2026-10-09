# Native device checks — pending APK build

These checks are deliberately unchecked: browser touch emulation cannot verify Android plugins or an actual APK.

- [ ] Build `app-debug.apk` using the documented SDK and JDK; record build output.
- [ ] Install on an API 24+ emulator or phone; verify MoneyFy icon and app name.
- [ ] Cold launch: branded Android splash followed by the rotating coin and tagline, without an artificial loading delay.
- [ ] Navigate all nine pages through bottom navigation and More.
- [ ] Check status/navigation insets on a notched phone, gesture navigation and three-button navigation.
- [ ] Rotate portrait/landscape and use the keyboard in goal/input dialogs; controls stay reachable.
- [ ] Android Back closes dialogs and drawer first, navigates pages, and minimizes at Home.
- [ ] Tap charts to inspect exact dates/values; drag every simulator slider; open exact-values table.
- [ ] Confirm/modify/reject/undo recommendations without executing money movement.
- [ ] Pick a synthetic CSV with the Android document picker and review normalization/duplicates.
- [ ] Export through the native save/share sheet; check destination content and cancellation behavior.
- [ ] Restart the process and confirm local goals/preferences persist.
- [ ] Delete/reset local data and verify it after process restart; previously exported external copies remain independent.
- [ ] Run the local demo in airplane mode.
- [ ] Configure a real trusted HTTPS API, sync/rebuild, and verify health request and explicit offline/timeout errors.
- [ ] Confirm API CORS allows the Android origin and that HTTP/untrusted TLS fails without bypasses.
- [ ] Re-run the website fallback after any shared UI changes.

Record device model, Android version, WebView version and findings when these checks are performed. No real banking credentials are needed for this hackathon demo.
