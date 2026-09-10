#!/usr/bin/env python3
import shutil
import sys
from pathlib import Path

VERSION = "3.31.1-billion-a9-test8"


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
        fail("usage: patch_remove_about_test8.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found")

    # Version
    props = studio / "release.properties"
    data = read(props)
    data = replace_once(data,
        "VERSION_NAME=3.31.1-billion-a9-test7",
        VERSION,
        "update Test8 version name")
    data = replace_once(data,
        "VERSION_CODE=331107",
        "VERSION_CODE=331108",
        "update Test8 version code")
    write(props, data)

    # Remove About from the home menu.
    menu = studio / "freeRDPCore/src/main/res/menu/home_menu.xml"
    data = read(menu)
    about_item = '''\n    <item
        android:id="@+id/about"
        android:icon="@drawable/ic_menu_about"
        app:showAsAction="ifRoom"
        android:title="@string/menu_about" />'''
    data = replace_once(data, about_item, "", "remove About menu item")
    write(menu, data)

    # Remove the About click handler.
    home = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/HomeActivity.java"
    data = read(home)
    about_handler = '''\t\telse if (itemId == R.id.about)
\t\t{
\t\t\tIntent aboutIntent = new Intent(this, AboutActivity.class);
\t\t\tstartActivity(aboutIntent);
\t\t}
'''
    data = replace_once(data, about_handler, "", "remove About click handler")
    write(home, data)

    # Remove AboutActivity from the app manifest, so it cannot be launched.
    manifest = studio / "freeRDPCore/src/main/AndroidManifest.xml"
    data = read(manifest)
    about_activity = '''        <activity
            android:exported="true"
            android:name=".presentation.AboutActivity"
            android:label="@string/title_about"
            android:theme="@style/Theme.Main"
            android:configChanges="orientation|keyboardHidden|screenSize" />
'''
    data = replace_once(data, about_activity, "", "remove About activity manifest entry")
    write(manifest, data)

    # Strip all upstream About HTML/images/assets from the APK.
    assets = studio / "aFreeRDP/src/main/assets"
    if assets.is_dir():
        for child in list(assets.iterdir()):
            if child.is_dir() and (child.name == "about_page" or child.name.endswith("_about_page")):
                shutil.rmtree(child)

    print("Test8 cleanup applied:", VERSION)
    print("About menu/activity/upstream About assets removed completely")


if __name__ == "__main__":
    main()
