#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def fail(msg):
    raise SystemExit("PATCH ERROR: " + msg)


def read(path):
    if not path.is_file():
        fail("missing file: " + str(path))
    return path.read_text(encoding="utf-8")


def write(path, data):
    path.write_text(data, encoding="utf-8", newline="\n")


def replace_once(data, old, new, desc):
    count = data.count(old)
    if count != 1:
        fail(f"{desc}: expected 1 match, found {count}")
    return data.replace(old, new, 1)


def main():
    if len(sys.argv) != 2:
        fail("usage: patch_konka_api28_test19.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"

    # Version metadata.
    props = studio / "release.properties"
    data = read(props)
    data = re.sub(r'^VERSION_NAME=.*$', 'VERSION_NAME=3.31.1-baihong-konka32-api28-test19', data, count=1, flags=re.M)
    data = re.sub(r'^VERSION_CODE=.*$', 'VERSION_CODE=331119', data, count=1, flags=re.M)
    write(props, data)

    # ------------------------------------------------------------------
    # CRITICAL Android 9 fix:
    # FileObserver(File, int) was added only in API 29. FreeRDP 3.31.x
    # constructs PrintJobMonitor from Application.onCreate(), so forcing
    # minSdk to 28 without changing this constructor causes NoSuchMethodError
    # on Android 9 before HomeActivity can render.
    # Keep the API-1 String constructor as a compatibility fallback.
    # ------------------------------------------------------------------
    monitor = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/PrintJobMonitor.java"
    data = read(monitor)
    data = replace_once(
        data,
        '\t\tsuper(new File(WATCH_DIR), CLOSE_WRITE);',
        '\t\tsuper(WATCH_DIR, CLOSE_WRITE);',
        'replace API29 FileObserver constructor')
    write(monitor, data)

    # Printing is irrelevant for the Konka signage target. On Android 9 do
    # not instantiate the monitor at all. On newer Android keep it available,
    # but never let a vendor-specific FileObserver problem kill the process.
    global_app = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/application/GlobalApp.java"
    data = read(global_app)
    if 'import android.os.Build;' not in data:
        data = replace_once(data, 'import android.os.Handler;\n', 'import android.os.Build;\nimport android.os.Handler;\n', 'import Build')

    old = '''\t\tprintJobMonitor = new PrintJobMonitor(file -> PrintNotificationHelper.notify(this, file));
\t\tprintJobMonitor.startWatching();'''
    new = '''\t\t// Test19: FreeRDP 3.31.x normally assumes API 29+.  Android 9/API 28
\t\t// must not enter the newer printing monitor startup path.
\t\tif (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q)
\t\t{
\t\t\ttry
\t\t\t{
\t\t\t\tprintJobMonitor = new PrintJobMonitor(file -> PrintNotificationHelper.notify(this, file));
\t\t\t\tprintJobMonitor.startWatching();
\t\t\t}
\t\t\tcatch (Throwable t)
\t\t\t{
\t\t\t\tLog.e(TAG, "Print monitor disabled after initialization failure", t);
\t\t\t\tprintJobMonitor = null;
\t\t\t}
\t\t}
\t\telse
\t\t{
\t\t\tLog.i(TAG, "Print monitor disabled for Android 9 compatibility");
\t\t\tprintJobMonitor = null;
\t\t}'''
    data = replace_once(data, old, new, 'guard print monitor startup')
    write(global_app, data)

    # Keep the first frame as simple as possible on non-standard vendor TV
    # firmware. The first-run guide is optional and can be accessed via
    # settings later; it must not participate in startup diagnostics.
    home = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/HomeActivity.java"
    data = read(home)
    data = data.replace('\t\tDeviceMode.maybeShowFirstRunGuide(this);\n', '', 1)
    write(home, data)

    # Verification guards for the patch itself.
    if 'super(new File(WATCH_DIR), CLOSE_WRITE);' in read(monitor):
        fail('API29 FileObserver constructor still present')
    if 'Build.VERSION_CODES.Q' not in read(global_app):
        fail('Android 9 print monitor guard missing')

    print('Test19 patch applied: Android 9 startup API mismatch fixed')


if __name__ == '__main__':
    main()
