#!/usr/bin/env python3
import re
import sys
from pathlib import Path

VERSION = "3.31.1-baihong-a9-legacy-test17"
VERSION_CODE = "331117"


def fail(msg):
    raise SystemExit("PATCH ERROR: " + msg)


def read(path):
    if not path.is_file():
        fail("missing file: " + str(path))
    return path.read_text(encoding="utf-8")


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8", newline="\n")


def replace_once(data, old, new, desc):
    count = data.count(old)
    if count != 1:
        fail(f"{desc}: expected 1 match, found {count}")
    return data.replace(old, new, 1)


def regex_replace_once(data, pattern, repl, desc, flags=0):
    out, count = re.subn(pattern, repl, data, count=1, flags=flags)
    if count != 1:
        fail(f"{desc}: expected 1 match, found {count}")
    return out


def set_string(data, name, value):
    pattern = re.compile(r'<string\s+name="' + re.escape(name) + r'"(?:\s+[^>]*)?>.*?</string>', re.S)
    repl = f'<string name="{name}">{value}</string>'
    if pattern.search(data):
        return pattern.sub(repl, data, count=1)
    pos = data.rfind("</resources>")
    if pos < 0:
        fail("strings.xml missing </resources>")
    return data[:pos] + "    " + repl + "\n" + data[pos:]


def main():
    if len(sys.argv) != 2:
        fail("usage: patch_baihong_legacy_test17.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found")

    # ------------------------------------------------------------------
    # 1. Runtime baseline: Android 9 is a real runtime target, not only a
    #    manifest minSdk value. Keep modern compile SDK but use an older,
    #    well proven NDK/CMake and conservative AndroidX runtime libraries.
    # ------------------------------------------------------------------
    props = studio / "release.properties"
    data = read(props)
    data = regex_replace_once(data, r'^MIN_API=.*$', 'MIN_API=28', 'set min API 28', re.M)
    data = regex_replace_once(data, r'^TARGET_API=.*$', 'TARGET_API=28', 'set target API 28', re.M)
    data = regex_replace_once(data, r'^COMPILE_API=.*$', 'COMPILE_API=36', 'set compile API 36', re.M)
    data = regex_replace_once(data, r'^TOOLS_VERSION=.*$', 'TOOLS_VERSION=36.0.0', 'set tools version', re.M)
    data = regex_replace_once(data, r'^NDK_VERSION=.*$', 'NDK_VERSION=25.2.9519653', 'use NDK r25c', re.M)
    data = regex_replace_once(data, r'^CMAKE_VERSION=.*$', 'CMAKE_VERSION=3.22.1', 'use CMake 3.22.1', re.M)
    data = regex_replace_once(data, r'^VERSION_NAME=.*$', 'VERSION_NAME=' + VERSION, 'set Test17 version', re.M)
    data = regex_replace_once(data, r'^VERSION_CODE=.*$', 'VERSION_CODE=' + VERSION_CODE, 'set Test17 code', re.M)
    # Force the native Android platform to API 28 as an additional guardrail.
    m = re.search(r'^CMAKE_ARGUMENTS=(.*)$', data, re.M)
    if not m:
        fail('CMAKE_ARGUMENTS missing')
    args = m.group(1)
    if '-DANDROID_PLATFORM=android-28' not in args:
        args += ';-DANDROID_PLATFORM=android-28'
    data = data[:m.start(1)] + args + data[m.end(1):]
    write(props, data)

    core_gradle = studio / "freeRDPCore/build.gradle"
    data = read(core_gradle)
    replacements = {
        r"androidx\.appcompat:appcompat:[^']+": "androidx.appcompat:appcompat:1.6.1",
        r"androidx\.core:core:[^']+": "androidx.core:core:1.12.0",
        r"androidx\.preference:preference:[^']+": "androidx.preference:preference:1.2.1",
        r"androidx\.recyclerview:recyclerview:[^']+": "androidx.recyclerview:recyclerview:1.3.2",
        r"androidx\.lifecycle:lifecycle-viewmodel:[^']+": "androidx.lifecycle:lifecycle-viewmodel:2.6.2",
        r"androidx\.lifecycle:lifecycle-livedata:[^']+": "androidx.lifecycle:lifecycle-livedata:2.6.2",
        r"androidx\.room:room-runtime:[^\"]+": "androidx.room:room-runtime:2.6.1",
        r"androidx\.room:room-compiler:[^\"]+": "androidx.room:room-compiler:2.6.1",
        r"net\.zetetic:sqlcipher-android:[^'@]+": "net.zetetic:sqlcipher-android:4.6.1",
        r"androidx\.sqlite:sqlite:[^']+": "androidx.sqlite:sqlite:2.4.0",
    }
    for pattern, repl in replacements.items():
        data, count = re.subn(pattern, repl, data)
        if count < 1:
            fail('dependency not found for legacy replacement: ' + pattern)
    write(core_gradle, data)

    app_gradle = studio / "aFreeRDP/build.gradle"
    data = read(app_gradle)
    # Test16 workflow added these explicitly; keep versions conservative if present.
    data = re.sub(r"androidx\.appcompat:appcompat:[^']+", "androidx.appcompat:appcompat:1.6.1", data)
    data = re.sub(r"androidx\.preference:preference:[^']+", "androidx.preference:preference:1.2.1", data)
    write(app_gradle, data)

    # ------------------------------------------------------------------
    # 2. Do NOT load FreeRDP native libraries from Application.onCreate.
    #    On old vendor Android 9 builds a linker/JNI incompatibility would
    #    otherwise kill the process before HomeActivity can draw anything.
    #    Native FreeRDP is initialized lazily on the first real RDP session.
    # ------------------------------------------------------------------
    global_app = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/application/GlobalApp.java"
    data = read(global_app)
    data = replace_once(data,
        '\tprivate PrintJobMonitor printJobMonitor;\n',
        '\tprivate PrintJobMonitor printJobMonitor;\n\tprivate volatile boolean nativeInitialized = false;\n',
        'add lazy native state')

    data = replace_once(data,
        '\t\tLibFreeRDP.setEventListener(this);\n\n',
        '\t\t// Test17: FreeRDP JNI is deliberately NOT loaded during app startup.\n\t\t// It is initialized lazily when the user actually starts an RDP session.\n\n',
        'remove eager native initialization')

    old_create_bookmark = '''\tstatic public SessionState createSession(BookmarkBase bookmark, Context context)\n\t{\n\t\tSessionState session = new SessionState(LibFreeRDP.newInstance(context), bookmark);\n'''
    new_create_bookmark = '''\tstatic public SessionState createSession(BookmarkBase bookmark, Context context)\n\t{\n\t\tensureNativeInitialized(context);\n\t\tSessionState session = new SessionState(LibFreeRDP.newInstance(context), bookmark);\n'''
    data = replace_once(data, old_create_bookmark, new_create_bookmark, 'lazy init bookmark session')

    old_create_uri = '''\tstatic public SessionState createSession(Uri openUri, Context context)\n\t{\n\t\tSessionState session = new SessionState(LibFreeRDP.newInstance(context), openUri);\n'''
    new_create_uri = '''\tstatic public SessionState createSession(Uri openUri, Context context)\n\t{\n\t\tensureNativeInitialized(context);\n\t\tSessionState session = new SessionState(LibFreeRDP.newInstance(context), openUri);\n'''
    data = replace_once(data, old_create_uri, new_create_uri, 'lazy init URI session')

    anchor = '\t// RDP session handling\n'
    helper = '''\tprivate synchronized void initializeNativeIfNeeded()\n\t{\n\t\tif (nativeInitialized)\n\t\t\treturn;\n\t\tLibFreeRDP.setEventListener(this);\n\t\tnativeInitialized = true;\n\t\tLog.i(TAG, "FreeRDP native runtime initialized lazily");\n\t}\n\n\tprivate static void ensureNativeInitialized(Context context)\n\t{\n\t\tContext appContext = context.getApplicationContext();\n\t\tif (!(appContext instanceof GlobalApp))\n\t\t\tthrow new IllegalStateException("Unexpected application context");\n\t\t((GlobalApp)appContext).initializeNativeIfNeeded();\n\t}\n\n'''
    data = replace_once(data, anchor, helper + anchor, 'add lazy native helpers')
    write(global_app, data)

    # ------------------------------------------------------------------
    # 3. Default-enabled resident foreground service. It starts only after
    #    the app itself has been launched; boot auto-start remains OFF by
    #    default and is controlled independently by the existing preference.
    # ------------------------------------------------------------------
    service = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/services/AppKeepAliveService.java"
    write(service, '''package com.freerdp.freerdpcore.services;\n\nimport android.app.Notification;\nimport android.app.NotificationChannel;\nimport android.app.NotificationManager;\nimport android.app.PendingIntent;\nimport android.app.Service;\nimport android.content.Context;\nimport android.content.Intent;\nimport android.os.Build;\nimport android.os.IBinder;\nimport android.util.Log;\n\nimport androidx.core.content.ContextCompat;\n\nimport com.freerdp.freerdpcore.R;\nimport com.freerdp.freerdpcore.presentation.ApplicationSettingsActivity;\nimport com.freerdp.freerdpcore.presentation.HomeActivity;\n\npublic class AppKeepAliveService extends Service\n{\n    private static final String TAG = "BaihongKeepAlive";\n    private static final String CHANNEL_ID = "baihong_rdp_keepalive";\n    private static final int NOTIFICATION_ID = 1701;\n\n    public static void applyPreference(Context context)\n    {\n        if (ApplicationSettingsActivity.getTvKeepAliveEnabled(context))\n            start(context);\n        else\n            stop(context);\n    }\n\n    public static void start(Context context)\n    {\n        try\n        {\n            Intent intent = new Intent(context, AppKeepAliveService.class);\n            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)\n                ContextCompat.startForegroundService(context, intent);\n            else\n                context.startService(intent);\n        }\n        catch (Throwable t)\n        {\n            // Keep-alive must never make an old vendor TV crash at startup.\n            Log.e(TAG, "Unable to start keep-alive service", t);\n        }\n    }\n\n    public static void stop(Context context)\n    {\n        try\n        {\n            context.stopService(new Intent(context, AppKeepAliveService.class));\n        }\n        catch (Throwable t)\n        {\n            Log.e(TAG, "Unable to stop keep-alive service", t);\n        }\n    }\n\n    @Override public void onCreate()\n    {\n        super.onCreate();\n        try\n        {\n            createChannel();\n            startForeground(NOTIFICATION_ID, buildNotification());\n        }\n        catch (Throwable t)\n        {\n            // Avoid process death on non-standard Android TV notification stacks.\n            Log.e(TAG, "Foreground keep-alive initialization failed", t);\n            stopSelf();\n        }\n    }\n\n    @Override public int onStartCommand(Intent intent, int flags, int startId)\n    {\n        if (!ApplicationSettingsActivity.getTvKeepAliveEnabled(this))\n        {\n            stopSelf();\n            return START_NOT_STICKY;\n        }\n        return START_STICKY;\n    }\n\n    @Override public IBinder onBind(Intent intent)\n    {\n        return null;\n    }\n\n    private void createChannel()\n    {\n        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O)\n            return;\n        NotificationManager manager = (NotificationManager)getSystemService(NOTIFICATION_SERVICE);\n        if (manager == null)\n            return;\n        NotificationChannel channel = new NotificationChannel(\n            CHANNEL_ID, "百宏RDP后台运行", NotificationManager.IMPORTANCE_MIN);\n        channel.setDescription("保持百宏RDP在后台稳定运行");\n        channel.setShowBadge(false);\n        manager.createNotificationChannel(channel);\n    }\n\n    private Notification buildNotification()\n    {\n        Intent launch = new Intent(this, HomeActivity.class);\n        launch.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);\n        int piFlags = PendingIntent.FLAG_UPDATE_CURRENT;\n        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M)\n            piFlags |= PendingIntent.FLAG_IMMUTABLE;\n        PendingIntent contentIntent = PendingIntent.getActivity(this, 0, launch, piFlags);\n\n        Notification.Builder builder;\n        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)\n            builder = new Notification.Builder(this, CHANNEL_ID);\n        else\n            builder = new Notification.Builder(this);\n\n        return builder\n            .setSmallIcon(R.drawable.ic_computer)\n            .setContentTitle("百宏RDP")\n            .setContentText("后台常驻运行中")\n            .setContentIntent(contentIntent)\n            .setOngoing(true)\n            .setCategory(Notification.CATEGORY_SERVICE)\n            .setPriority(Notification.PRIORITY_MIN)\n            .build();\n    }\n}\n''')

    manifest = studio / "freeRDPCore/src/main/AndroidManifest.xml"
    data = read(manifest)
    if 'android.permission.FOREGROUND_SERVICE' not in data:
        data = replace_once(data,
            '    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />\n',
            '    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />\n'
            '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />\n',
            'add foreground service permission')
    service_anchor = '''        <service\n            android:name=".presentation.KeyboardAccessibilityService"\n'''
    service_decl = '''        <service\n            android:name=".services.AppKeepAliveService"\n            android:enabled="true"\n            android:exported="false" />\n\n'''
    data = replace_once(data, service_anchor, service_decl + service_anchor, 'declare keep-alive service')
    write(manifest, data)

    home = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/HomeActivity.java"
    data = read(home)
    import_anchor = 'import com.freerdp.freerdpcore.utils.RDPFileHelper;\n'
    data = replace_once(data, import_anchor,
        import_anchor + 'import com.freerdp.freerdpcore.services.AppKeepAliveService;\n',
        'import keep-alive service')
    set_content = '\t\tsetContentView(binding.getRoot());\n'
    data = replace_once(data, set_content,
        set_content + '\n\t\t// Default ON; independent from boot auto-start.\n\t\tAppKeepAliveService.applyPreference(this);\n',
        'start keep-alive after Home UI exists')
    write(home, data)

    settings = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/ApplicationSettingsActivity.java"
    data = read(settings)
    import_marker = 'import com.freerdp.freerdpcore.R;\n'
    if 'AppKeepAliveService' not in data:
        data = replace_once(data, import_marker,
            import_marker + 'import com.freerdp.freerdpcore.services.AppKeepAliveService;\n',
            'import keep-alive in settings')

    helper_anchor = '\tpublic static boolean getTvAutoConnectEnabled(Context context)\n'
    keep_helper = '''\tpublic static boolean getTvKeepAliveEnabled(Context context)\n\t{\n\t\treturn get(context).getBoolean("tv.keep_alive", true);\n\t}\n\n'''
    data = replace_once(data, helper_anchor, keep_helper + helper_anchor, 'add keep-alive preference helper')

    tv_set = '\t\t\tsetPreferencesFromResource(R.xml.settings_app_tv, rootKey);\n'
    tv_hook = '''\t\t\tPreference keepAlive = findPreference("tv.keep_alive");\n\t\t\tif (keepAlive != null)\n\t\t\t{\n\t\t\t\tkeepAlive.setOnPreferenceChangeListener((pref, newValue) -> {\n\t\t\t\t\tif (Boolean.TRUE.equals(newValue))\n\t\t\t\t\t\tAppKeepAliveService.start(requireContext());\n\t\t\t\t\telse\n\t\t\t\t\t\tAppKeepAliveService.stop(requireContext());\n\t\t\t\t\treturn true;\n\t\t\t\t});\n\t\t\t}\n'''
    data = replace_once(data, tv_set, tv_set + tv_hook, 'hook keep-alive switch')
    write(settings, data)

    tv_xml = studio / "freeRDPCore/src/main/res/xml/settings_app_tv.xml"
    data = read(tv_xml)
    boot_key = 'android:key="tv.start_on_boot"'
    pos = data.find(boot_key)
    if pos < 0:
        fail('boot preference missing')
    start = data.rfind('<SwitchPreferenceCompat', 0, pos)
    end = data.find('/>', pos)
    if start < 0 or end < 0:
        fail('boot preference block missing')
    end += 2
    boot_block = data[start:end]
    # Explicitly keep boot auto-start disabled by default.
    boot_block = re.sub(r'android:defaultValue="[^"]+"', 'android:defaultValue="false"', boot_block, count=1)
    keep_block = '''\n    <SwitchPreferenceCompat\n        android:key="tv.keep_alive"\n        android:defaultValue="true"\n        android:title="@string/settings_tv_keep_alive"\n        android:summary="@string/settings_tv_keep_alive_summary" />'''
    data = data[:start] + boot_block + keep_block + data[end:]
    write(tv_xml, data)

    en_path = studio / "freeRDPCore/src/main/res/values/strings.xml"
    zh_path = studio / "freeRDPCore/src/main/res/values-zh/strings.xml"
    en = read(en_path)
    en = set_string(en, 'settings_tv_keep_alive', 'Keep app resident in background')
    en = set_string(en, 'settings_tv_keep_alive_summary', 'Enabled by default. Uses a foreground service after the app is opened; boot auto-start is controlled separately.')
    write(en_path, en)
    zh = read(zh_path)
    zh = set_string(zh, 'settings_tv_keep_alive', '后台常驻运行')
    zh = set_string(zh, 'settings_tv_keep_alive_summary', '默认开启。打开百宏RDP后保持后台常驻；开机自动启动需要单独手工开启。')
    write(zh_path, zh)

    # Final static guardrails.
    if 'android:defaultValue="true"' not in read(tv_xml) or 'tv.keep_alive' not in read(tv_xml):
        fail('keep-alive default ON verification failed')
    tv = read(tv_xml)
    boot_pos = tv.find('android:key="tv.start_on_boot"')
    boot_start = tv.rfind('<SwitchPreferenceCompat', 0, boot_pos)
    boot_end = tv.find('/>', boot_pos) + 2
    if 'android:defaultValue="false"' not in tv[boot_start:boot_end]:
        fail('boot auto-start must remain default OFF')
    if 'LibFreeRDP.setEventListener(this);' in read(global_app).split('@Override public void onCreate()', 1)[1].split('// helper to send FreeRDP notifications', 1)[0]:
        fail('native library is still eagerly initialized during Application.onCreate')

    print('Test17 Android 9 legacy runtime patch applied:', VERSION)
    print('Keep-alive: default ON; boot auto-start: default OFF')
    print('Native FreeRDP: lazy initialization on first session')
    print('Runtime libs: conservative AndroidX; NDK r25c; native platform android-28')


if __name__ == '__main__':
    main()
