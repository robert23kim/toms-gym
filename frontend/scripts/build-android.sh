#!/usr/bin/env bash
set -euo pipefail

# ─── Android APK Build Script for Tom's Gym ───
# Builds the React app, syncs to Capacitor, and produces a debug or release APK.
#
# Usage:
#   ./scripts/build-android.sh              # Debug APK (no signing needed)
#   ./scripts/build-android.sh --release    # Signed release APK
#   ./scripts/build-android.sh --install    # Build debug + install on connected device
#
# Prerequisites (auto-installed if missing):
#   - Node.js + npm
#   - Java 17+ (via Homebrew)
#   - Android SDK command-line tools (via Homebrew)

FRONTEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ANDROID_DIR="$FRONTEND_DIR/android"
BUILD_TYPE="debug"
INSTALL=false
KEYSTORE_PATH="$FRONTEND_DIR/android/tomsgym-release.keystore"

for arg in "$@"; do
  case $arg in
    --release) BUILD_TYPE="release" ;;
    --install) INSTALL=true ;;
    --help|-h)
      echo "Usage: $0 [--release] [--install]"
      echo "  --release   Build signed release APK (will prompt for keystore if missing)"
      echo "  --install   Install APK on connected device/emulator after build"
      exit 0
      ;;
  esac
done

# ─── Colors ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ─── Step 1: Check / Install Dependencies ───
info "Checking dependencies..."

# Java 21 — required by Capacitor 8.x / Android Gradle Plugin
JAVA21_HOME="/opt/homebrew/opt/openjdk@21"
if [ -d "$JAVA21_HOME" ]; then
  export JAVA_HOME="$JAVA21_HOME"
  export PATH="$JAVA_HOME/bin:$PATH"
elif /usr/libexec/java_home -v 21 &>/dev/null; then
  export JAVA_HOME=$(/usr/libexec/java_home -v 21)
  export PATH="$JAVA_HOME/bin:$PATH"
else
  warn "Java 21 not found. Installing via Homebrew..."
  brew install openjdk@21
  export JAVA_HOME="/opt/homebrew/opt/openjdk@21"
  export PATH="$JAVA_HOME/bin:$PATH"
  info "Java 21 installed."
fi
info "Java: $(java -version 2>&1 | head -1)"

# Android SDK
ANDROID_HOME="${ANDROID_HOME:-}"
if [ -z "$ANDROID_HOME" ]; then
  # Check common locations in order of preference
  for candidate in \
    "$HOME/Library/Android/sdk" \
    "/opt/homebrew/share/android-commandlinetools" \
    "/usr/local/share/android-commandlinetools"; do
    if [ -d "$candidate" ]; then
      export ANDROID_HOME="$candidate"
      break
    fi
  done
fi

if [ -z "$ANDROID_HOME" ] || [ ! -d "$ANDROID_HOME" ]; then
  warn "Android SDK not found. Installing command-line tools via Homebrew..."
  brew install --cask android-commandlinetools
  export ANDROID_HOME="$(brew --prefix)/share/android-commandlinetools"
  info "Android command-line tools installed at $ANDROID_HOME"
fi

export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/build-tools/35.0.0:$PATH"
info "ANDROID_HOME: $ANDROID_HOME"

# Accept licenses and install required SDK components
if [ -f "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" ]; then
  yes | sdkmanager --licenses > /dev/null 2>&1 || true
  REQUIRED_PACKAGES=("platform-tools" "platforms;android-35" "build-tools;35.0.0")
  for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if ! sdkmanager --list_installed 2>/dev/null | grep -q "${pkg%%;}"; then
      info "Installing SDK package: $pkg"
      sdkmanager "$pkg" 2>&1 | tail -1
    fi
  done
fi

# Write local.properties so Gradle can find the SDK
echo "sdk.dir=$ANDROID_HOME" > "$ANDROID_DIR/local.properties"

# ─── Step 2: Build React App ───
info "Building React app..."
cd "$FRONTEND_DIR"
npm run build

# ─── Step 3: Sync to Android ───
info "Syncing to Android project..."
npx cap sync android

# ─── Step 4: Build APK ───
cd "$ANDROID_DIR"

if [ "$BUILD_TYPE" = "release" ]; then
  # Release build — needs a keystore
  if [ ! -f "$KEYSTORE_PATH" ]; then
    info "No keystore found. Creating one..."
    echo ""
    echo "You'll be prompted for a keystore password and some identity info."
    echo "Remember the password — you need it for every future release."
    echo ""
    keytool -genkeypair \
      -v \
      -storetype PKCS12 \
      -keystore "$KEYSTORE_PATH" \
      -keyalg RSA \
      -keysize 2048 \
      -validity 10000 \
      -alias tomsgym
    echo ""
    info "Keystore created at $KEYSTORE_PATH"
    warn "Back this file up! Losing it means you can never update the app."
  fi

  # Prompt for keystore password
  echo ""
  read -sp "Keystore password: " KS_PASS
  echo ""

  # Build unsigned release APK, then sign it
  info "Building release APK..."
  ./gradlew assembleRelease -q

  UNSIGNED_APK="$ANDROID_DIR/app/build/outputs/apk/release/app-release-unsigned.apk"
  SIGNED_APK="$FRONTEND_DIR/tomsgym-release.apk"

  if [ ! -f "$UNSIGNED_APK" ]; then
    error "Release APK not found at $UNSIGNED_APK"
  fi

  # Sign
  info "Signing APK..."
  cp "$UNSIGNED_APK" "$SIGNED_APK"
  jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
    -keystore "$KEYSTORE_PATH" \
    -storepass "$KS_PASS" \
    "$SIGNED_APK" tomsgym 2>&1 | tail -3

  # Zipalign if available
  if command -v zipalign &>/dev/null; then
    ALIGNED_APK="$FRONTEND_DIR/tomsgym-release-aligned.apk"
    zipalign -v 4 "$SIGNED_APK" "$ALIGNED_APK" > /dev/null 2>&1
    mv "$ALIGNED_APK" "$SIGNED_APK"
    info "APK aligned."
  elif [ -f "$ANDROID_HOME/build-tools/35.0.0/zipalign" ]; then
    ALIGNED_APK="$FRONTEND_DIR/tomsgym-release-aligned.apk"
    "$ANDROID_HOME/build-tools/35.0.0/zipalign" -v 4 "$SIGNED_APK" "$ALIGNED_APK" > /dev/null 2>&1
    mv "$ALIGNED_APK" "$SIGNED_APK"
    info "APK aligned."
  fi

  APK_PATH="$SIGNED_APK"
  info "Release APK: $APK_PATH"

else
  # Debug build — no signing needed
  info "Building debug APK..."
  ./gradlew assembleDebug -q

  APK_PATH="$ANDROID_DIR/app/build/outputs/apk/debug/app-debug.apk"

  if [ ! -f "$APK_PATH" ]; then
    error "Debug APK not found at $APK_PATH"
  fi

  # Copy to a convenient location
  cp "$APK_PATH" "$FRONTEND_DIR/tomsgym-debug.apk"
  APK_PATH="$FRONTEND_DIR/tomsgym-debug.apk"
  info "Debug APK: $APK_PATH"
fi

# ─── Step 5: Install (optional) ───
if [ "$INSTALL" = true ]; then
  ADB="adb"
  if ! command -v adb &>/dev/null; then
    ADB="$ANDROID_HOME/platform-tools/adb"
  fi

  if ! "$ADB" devices | grep -q "device$"; then
    warn "No device/emulator connected. Skipping install."
    warn "Connect a device with USB debugging enabled and run:"
    warn "  adb install $APK_PATH"
  else
    info "Installing on device..."
    "$ADB" install -r "$APK_PATH"
    info "Installed! Opening app..."
    "$ADB" shell am start -n com.tomsgym.app/.MainActivity
  fi
fi

# ─── Done ───
APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
echo ""
info "Build complete!"
info "APK: $APK_PATH ($APK_SIZE)"
echo ""
echo "To install on a connected device:"
echo "  adb install $APK_PATH"
echo ""
echo "To share: send the APK file via AirDrop, Messages, or Google Drive."
