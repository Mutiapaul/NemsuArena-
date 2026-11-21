# Android companion app

This is the Android wrapper for Anyo Arena's local game. It opens the host's game in a WebView, supports the fighter image picker, and uses the same touch controls as the browser version.

## Build a debug APK

1. Open this `android` directory as a project in Android Studio with the Android SDK and JDK 17 installed.
2. Allow Gradle to sync and install the required Android SDK Platform 35 if prompted.
3. Choose **Build > Build Bundle(s) / APK(s) > Build APK(s)**. The generated debug APK is in `app/build/outputs/apk/debug/app-debug.apk`.
4. Transfer the APK to each Android phone and install it. On first launch, enter the host's private IP address. All phones must be on the same Wi-Fi or hotspot.

The **game server still needs to run** (`python3 server.py`) on a laptop, Chromebook with Linux, or a phone running a Python environment. If the server is on the same Android phone as this wrapper, enter `127.0.0.1`; other players enter that host phone's Wi-Fi IP address. The Android app itself does not host the game yet.

The root `.github/workflows/android-apk.yml` also builds and uploads a debug APK when the entire source tree is pushed to a GitHub repository and its **Build Anyo Arena APK** workflow is run. The workflow has not been run here, so its artifact is not tested. This directory intentionally includes source code, not a prebuilt APK. No Android SDK or Gradle is bundled in the ZIP.
