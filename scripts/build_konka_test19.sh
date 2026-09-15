#!/usr/bin/env bash
set -euo pipefail

FREERDP_COMMIT="50c9f7470d9da3a45e1ebb5ee5fba14140c3fbb3"
ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-/usr/local/lib/android/sdk}"
ANDROID_HOME="$ANDROID_SDK_ROOT"
export ANDROID_SDK_ROOT ANDROID_HOME

sudo apt-get update
sudo apt-get install -y git perl make ninja-build pkg-config python3 python3-pip autoconf automake libtool gettext zip unzip
python3 -m pip install --break-system-packages "cryptography==46.0.4"

SDKMANAGER="$(find "$ANDROID_SDK_ROOT/cmdline-tools" -type f -name sdkmanager 2>/dev/null | sort | tail -n 1)"
test -n "$SDKMANAGER"
yes | "$SDKMANAGER" --licenses >/dev/null || true
"$SDKMANAGER" "platform-tools" "platforms;android-36" "build-tools;36.0.0" "ndk;25.2.9519653" "cmake;3.22.1"

rm -rf upstream output
mkdir upstream output
git -C upstream init -q
git -C upstream remote add origin https://github.com/FreeRDP/FreeRDP.git
for n in 1 2 3 4 5; do
  if git -C upstream fetch --depth=1 origin "$FREERDP_COMMIT"; then break; fi
  if [ "$n" = 5 ]; then exit 1; fi
  sleep $((n * 8))
done
git -C upstream checkout -q FETCH_HEAD

for f in \
  patch_freerdp_tv_test3.py patch_adaptive_test4.py patch_brand_ux_test5.py \
  patch_billion_brand_test6.py patch_ux_errors_test7.py patch_remove_about_test8.py \
  patch_tv_focus_display_test9.py patch_stability_test10.py patch_tv_always_on_test11.py \
  patch_tv_remote_hd_test12.py patch_chinese_ui_test13.py patch_baihong_stable_test16.py \
  patch_baihong_legacy_test17.py patch_konka32_test18.py patch_konka_api28_test19.py \
  generate_test_signing.py; do
  python3 -m py_compile "scripts/$f"
done

python3 scripts/patch_freerdp_tv_test3.py upstream
STUDIO=upstream/client/Android/Studio
sed -i 's/^COMPILE_API=.*/COMPILE_API=36/' "$STUDIO/release.properties"
sed -i 's/^TOOLS_VERSION=.*/TOOLS_VERSION=36.0.0/' "$STUDIO/release.properties"
sed -i "s/androidx.core:core:1.19.0/androidx.core:core:1.18.0/" "$STUDIO/freeRDPCore/build.gradle"
sed -i "s/androidx.lifecycle:lifecycle-viewmodel:2.11.0/androidx.lifecycle:lifecycle-viewmodel:2.10.0/" "$STUDIO/freeRDPCore/build.gradle"
sed -i "s/androidx.lifecycle:lifecycle-livedata:2.11.0/androidx.lifecycle:lifecycle-livedata:2.10.0/" "$STUDIO/freeRDPCore/build.gradle"
sed -i "s/sqlcipher-android:4.17.0/sqlcipher-android:4.16.0/" "$STUDIO/freeRDPCore/build.gradle"
sed -i "s/androidx.sqlite:sqlite:2.7.0/androidx.sqlite:sqlite:2.6.2/" "$STUDIO/freeRDPCore/build.gradle"
sed -i "/implementation project(':freeRDPCore')/a\\    implementation 'androidx.appcompat:appcompat:1.7.1'\n    implementation 'androidx.preference:preference:1.2.1'" "$STUDIO/aFreeRDP/build.gradle"

python3 scripts/patch_adaptive_test4.py upstream
python3 scripts/patch_brand_ux_test5.py upstream
python3 scripts/patch_billion_brand_test6.py upstream
python3 scripts/patch_ux_errors_test7.py upstream
python3 scripts/patch_remove_about_test8.py upstream
python3 scripts/patch_tv_focus_display_test9.py upstream
python3 scripts/patch_stability_test10.py upstream
python3 scripts/patch_tv_always_on_test11.py upstream
python3 scripts/patch_tv_remote_hd_test12.py upstream
python3 scripts/patch_chinese_ui_test13.py upstream
python3 scripts/patch_baihong_stable_test16.py upstream
python3 scripts/patch_baihong_legacy_test17.py upstream
python3 scripts/patch_konka32_test18.py upstream
python3 scripts/patch_konka_api28_test19.py upstream

python3 scripts/generate_test_signing.py "$STUDIO/billion-rdp-test.p12" | tee /tmp/signing.txt

grep -F "VERSION_NAME=3.31.1-baihong-konka32-api28-test19" "$STUDIO/release.properties"
grep -F "MIN_API=28" "$STUDIO/release.properties"
grep -F "TARGET_API=28" "$STUDIO/release.properties"
grep -F "ABI_FILTERS=armeabi-v7a" "$STUDIO/release.properties"
grep -F -- "-DANDROID_PLATFORM=android-28" "$STUDIO/release.properties"
! grep -Fq 'sqlcipher-android' "$STUDIO/freeRDPCore/build.gradle"
! grep -Fq 'super(new File(WATCH_DIR), CLOSE_WRITE)' "$STUDIO/freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/PrintJobMonitor.java"
grep -Fq 'Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q' "$STUDIO/freeRDPCore/src/main/java/com/freerdp/freerdpcore/application/GlobalApp.java"
! grep -Fq 'android:scheme="Rdp"' "$STUDIO/aFreeRDP/src/main/AndroidManifest.xml"

pushd "$STUDIO" >/dev/null
chmod +x gradlew
# Record the final dependency graph. checkReleaseAarMetadata, which is pulled by
# assemble/lint, rejects Android libraries whose metadata is incompatible with
# this application's SDK configuration.
./gradlew --no-daemon :aFreeRDP:dependencies --configuration releaseRuntimeClasspath \
  2>&1 | tee "$GITHUB_WORKSPACE/output/DEPENDENCIES.txt"

# Assemble first, then lint BOTH the app and core library against minSdk 28.
# NewApi is a hard compatibility gate; any API 29+ call that is not correctly
# guarded must prevent this APK from being published.
./gradlew --no-daemon --stacktrace :aFreeRDP:assembleRelease \
  2>&1 | tee "$GITHUB_WORKSPACE/output/GRADLE_BUILD.txt"
./gradlew --no-daemon --stacktrace :freeRDPCore:lintRelease :aFreeRDP:lintRelease \
  2>&1 | tee "$GITHUB_WORKSPACE/output/LINT_BUILD.txt"
popd >/dev/null

# Preserve the machine-readable lint reports and explicitly reject NewApi even
# if a future lint severity/default changes.
find "$STUDIO" -path '*/build/intermediates/lint_intermediate_text_report/*/lint-results-*.txt' -type f -print -exec cat {} \; \
  > "$GITHUB_WORKSPACE/output/LINT_ALL.txt" || true
if grep -Fq '[NewApi]' "$GITHUB_WORKSPACE/output/LINT_ALL.txt"; then
  echo 'Android 9 compatibility gate failed: NewApi finding present' >&2
  exit 1
fi
if grep -Eiq 'requires api level (29|3[0-9])|call requires api level (29|3[0-9])' "$GITHUB_WORKSPACE/output/LINT_ALL.txt"; then
  echo 'Android 9 compatibility gate failed: API 29+ requirement present' >&2
  exit 1
fi

APK="$(find "$STUDIO/aFreeRDP/build/outputs/apk/release" -type f -name '*.apk' | sort | head -n 1)"
test -n "$APK"
OUT="$GITHUB_WORKSPACE/output/BAIHONG-RDP-3.31.1-Android9-KONKA32-Test19.apk"
cp "$APK" "$OUT"

AAPT="$ANDROID_SDK_ROOT/build-tools/36.0.0/aapt"
APKSIGNER="$ANDROID_SDK_ROOT/build-tools/36.0.0/apksigner"
ZIPALIGN="$ANDROID_SDK_ROOT/build-tools/36.0.0/zipalign"
sha256sum "$OUT" | tee "$GITHUB_WORKSPACE/output/SHA256.txt"
"$AAPT" dump badging "$OUT" | tee "$GITHUB_WORKSPACE/output/APK_BADGING.txt"
grep -Fq "sdkVersion:'28'" "$GITHUB_WORKSPACE/output/APK_BADGING.txt"
grep -Fq "targetSdkVersion:'28'" "$GITHUB_WORKSPACE/output/APK_BADGING.txt"
grep -Fq "versionName='3.31.1-baihong-konka32-api28-test19'" "$GITHUB_WORKSPACE/output/APK_BADGING.txt"
"$APKSIGNER" verify --verbose --print-certs "$OUT" | tee "$GITHUB_WORKSPACE/output/APK_SIGNATURE.txt"
"$ZIPALIGN" -c -v 4 "$OUT" >/dev/null
unzip -t "$OUT" | tee "$GITHUB_WORKSPACE/output/APK_ZIP_TEST.txt"
unzip -l "$OUT" | grep -F "lib/armeabi-v7a/"
if unzip -l "$OUT" | grep -Eq 'lib/(arm64-v8a|x86|x86_64|riscv64)/'; then exit 1; fi
if unzip -l "$OUT" | grep -Fiq 'sqlcipher'; then exit 1; fi

cat > "$GITHUB_WORKSPACE/output/BUILD_INFO.txt" <<'EOF'
百宏RDP Test19 - Konka Android 9 / API28 compatibility build
ABI: armeabi-v7a only
minSdk=28; targetSdk=28
Native platform: android-28 (NDK r25c)
Confirmed fix: FileObserver(File,int) API29 startup call removed
Android 9: print monitor disabled before construction
Android URI scheme normalized to lowercase rdp
Android lintRelease: app + freeRDPCore passed
Explicit NewApi/API29+ lint gate: passed
AAR metadata/dependency compatibility checks: passed during build
Bookmark DB: standard Room/SQLite
SQLCipher startup path removed
FreeRDP JNI lazy-loaded on first session
Keep-alive default ON and delayed after Home is shown
Boot auto-start default OFF
EOF
