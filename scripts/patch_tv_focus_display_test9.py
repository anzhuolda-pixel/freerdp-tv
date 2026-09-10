#!/usr/bin/env python3
import sys
from pathlib import Path

VERSION = "3.31.1-billion-a9-test9"

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

def insert_before_last(data, marker, addition, desc):
    pos = data.rfind(marker)
    if pos < 0:
        fail(desc + ": marker not found")
    return data[:pos] + addition + data[pos:]

def main():
    if len(sys.argv) != 2:
        fail("usage: patch_tv_focus_display_test9.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found")

    props = studio / "release.properties"
    data = read(props)
    data = replace_once(data, "VERSION_NAME=3.31.1-billion-a9-test8",
                        "VERSION_NAME=" + VERSION, "update Test9 version")
    data = replace_once(data, "VERSION_CODE=331108", "VERSION_CODE=331109",
                        "update Test9 version code")
    write(props, data)

    device_mode = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/DeviceMode.java"
    data = read(device_mode)
    additions = '''
    public static boolean shouldShowFloatingToolbar(Context context)
    {
        String mode = PreferenceManager.getDefaultSharedPreferences(context)
            .getString("ui.floating_toolbar_mode", "auto");
        if ("show".equals(mode))
            return true;
        if ("hide".equals(mode))
            return false;
        return !isTv(context);
    }
'''
    data = insert_before_last(data, "\n}\n", additions, "add floating-toolbar mode helper")
    write(device_mode, data)

    settings_tv = studio / "freeRDPCore/src/main/res/xml/settings_app_tv.xml"
    data = read(settings_tv)
    toolbar_pref = '''
    <ListPreference
        android:key="ui.floating_toolbar_mode"
        android:defaultValue="auto"
        android:title="@string/settings_floating_toolbar"
        android:summary="@string/settings_floating_toolbar_summary"
        android:entries="@array/floating_toolbar_entries"
        android:entryValues="@array/floating_toolbar_values"
        app:useSimpleSummaryProvider="true" />

'''
    data = data.replace("</PreferenceScreen>", toolbar_pref + "</PreferenceScreen>", 1)
    write(settings_tv, data)

    session = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/SessionActivity.java"
    data = read(session)
    toolbar_anchor = '''\t\tfloatingToolbar = new FloatingToolbar(this, new FloatingToolbar.Listener() {
\t\t\t@Override public void onToggleTouchPointer()
\t\t\t{
\t\t\t\tif (inputManager != null)
\t\t\t\t\tinputManager.toggleTouchPointer();
\t\t\t}
\t\t\t@Override public void onToggleKeyboard()
\t\t\t{
\t\t\t\tif (inputManager != null)
\t\t\t\t\tinputManager.toggleKeyboard();
\t\t\t}
\t\t});

\t\tExtendedKeyboardView keyboard = findViewById(R.id.extended_keyboard);
'''
    toolbar_new = toolbar_anchor.replace(
        "\n\t\tExtendedKeyboardView keyboard",
        '''
\t\tView floatingToolbarView = findViewById(R.id.floating_toolbar_container);
\t\tif (floatingToolbarView != null)
\t\t\tfloatingToolbarView.setVisibility(
\t\t\t    DeviceMode.shouldShowFloatingToolbar(this) ? View.VISIBLE : View.GONE);

\t\tExtendedKeyboardView keyboard'''
    )
    data = replace_once(data, toolbar_anchor, toolbar_new,
                        "apply automatic floating-toolbar visibility")
    write(session, data)

    bookmark = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/BookmarkActivity.java"
    data = read(bookmark)
    data = replace_once(data, "import android.view.MenuItem;\n",
                        "import android.view.MenuItem;\nimport android.view.KeyEvent;\nimport android.view.inputmethod.EditorInfo;\nimport android.widget.EditText;\n",
                        "add TV edit dialog Android imports")
    data = replace_once(data, "import androidx.preference.Preference;\n",
                        "import androidx.preference.Preference;\nimport androidx.preference.EditTextPreference;\nimport androidx.preference.EditTextPreferenceDialogFragmentCompat;\nimport androidx.preference.ListPreference;\nimport androidx.preference.PreferenceCategory;\n",
                        "add preference dialog imports")
    for name in ["MainFragment", "CredentialsFragment", "ScreenFragment",
                 "PerformanceFragment", "AdvancedFragment", "GatewayFragment", "DebugFragment"]:
        data = replace_once(
            data,
            f"public static class {name} extends PreferenceFragmentCompat",
            f"public static class {name} extends BillionPreferenceFragment",
            f"make {name} TV-aware"
        )

    base_fragment = '''
    /**
     * TV-friendly EditTextPreference dialogs:
     * DOWN from the edit field selects Confirm; keyboard Done confirms.
     * Cancel remains reachable from Confirm with left/right.
     */
    public static abstract class BillionPreferenceFragment extends PreferenceFragmentCompat
    {
        @Override public void onDisplayPreferenceDialog(Preference preference)
        {
            if (preference instanceof EditTextPreference)
            {
                BillionEditTextDialog dialog =
                    BillionEditTextDialog.newInstance(preference.getKey());
                dialog.setTargetFragment(this, 0);
                dialog.show(getParentFragmentManager(), "billion.edit");
                return;
            }
            super.onDisplayPreferenceDialog(preference);
        }
    }

    public static class BillionEditTextDialog extends EditTextPreferenceDialogFragmentCompat
    {
        public static BillionEditTextDialog newInstance(String key)
        {
            BillionEditTextDialog fragment = new BillionEditTextDialog();
            Bundle args = new Bundle();
            args.putString("key", key);
            fragment.setArguments(args);
            return fragment;
        }

        @Override public void onStart()
        {
            super.onStart();
            if (!DeviceMode.isTv(requireContext()) || getDialog() == null)
                return;

            android.app.Dialog dialog = getDialog();
            EditText edit = dialog.findViewById(android.R.id.edit);
            android.widget.Button positive = dialog.findViewById(android.R.id.button1);
            if (edit == null || positive == null)
                return;

            edit.setSingleLine(true);
            edit.setImeOptions(EditorInfo.IME_ACTION_DONE);
            edit.setOnEditorActionListener((v, actionId, event) -> {
                boolean enter = event != null &&
                    event.getAction() == KeyEvent.ACTION_DOWN &&
                    event.getKeyCode() == KeyEvent.KEYCODE_ENTER;
                if (actionId == EditorInfo.IME_ACTION_DONE ||
                    actionId == EditorInfo.IME_ACTION_GO || enter)
                {
                    positive.performClick();
                    return true;
                }
                return false;
            });
            edit.setOnKeyListener((v, keyCode, event) -> {
                if (keyCode == KeyEvent.KEYCODE_DPAD_DOWN &&
                    event.getAction() == KeyEvent.ACTION_DOWN)
                {
                    positive.requestFocus();
                    return true;
                }
                return false;
            });
        }
    }

'''
    marker = "\t/** Root screen loaded by the activity on start-up. */\n"
    data = replace_once(data, marker, base_fragment + marker,
                        "insert TV-aware preference dialog helpers")

    screen_create = '''\t\t\tsetPreferencesFromResource(R.xml.screen_settings, rootKey);
\t\t\tapplyInitialScreenState();
\t\t\tsetIntSummaryProvider();
'''
    screen_create_new = '''\t\t\tsetPreferencesFromResource(R.xml.screen_settings, rootKey);
\t\t\tconfigureDisplayForDevice();
\t\t\tapplyInitialScreenState();
\t\t\tsetIntSummaryProvider();
'''
    data = replace_once(data, screen_create, screen_create_new,
                        "configure device-specific display page")

    apply_anchor = '''\t\tprivate void applyInitialScreenState()
\t\t{
'''
    display_method = '''\t\tprivate void configureDisplayForDevice()
\t\t{
\t\t\tPreference tvGuide = findPreference("bookmark.tv_display_guide");
\t\t\tPreferenceCategory scaleCategory = findPreference("bookmark.scale_category");
\t\t\tif (!DeviceMode.isTv(requireContext()))
\t\t\t{
\t\t\t\tif (tvGuide != null)
\t\t\t\t\tgetPreferenceScreen().removePreference(tvGuide);
\t\t\t\treturn;
\t\t\t}

\t\t\tSharedPreferences prefs = getPreferenceManager().getSharedPreferences();
\t\t\tBookmarkViewModel vm =
\t\t\t    new ViewModelProvider(requireActivity()).get(BookmarkViewModel.class);
\t\t\tif (vm.isNewBookmark())
\t\t\t{
\t\t\t\tprefs.edit()
\t\t\t\t    .putString("bookmark.resolution", "automatic")
\t\t\t\t    .putInt("bookmark.colors", 32)
\t\t\t\t    .putString("bookmark.scale_mode", "100")
\t\t\t\t    .putInt("bookmark.scale_desktop", 100)
\t\t\t\t    .putInt("bookmark.scale_device", 100)
\t\t\t\t    .apply();
\t\t\t}

\t\t\tPreference resolution = findPreference("bookmark.resolution");
\t\t\tif (resolution instanceof ListPreference)
\t\t\t{
\t\t\t\tListPreference list = (ListPreference)resolution;
\t\t\t\tlist.setEntries(R.array.tv_resolutions_array);
\t\t\t\tlist.setEntryValues(R.array.tv_resolutions_values_array);
\t\t\t}

\t\t\tif (scaleCategory != null)
\t\t\t\tgetPreferenceScreen().removePreference(scaleCategory);
\t\t}

''' + apply_anchor
    data = replace_once(data, apply_anchor, display_method,
                        "add simplified TV display configuration")
    data = replace_once(data, 'return res + "@" + colors;',
                        'return getString(R.string.settings_screen_summary_format, res, colors);',
                        "make display summary human-readable")
    write(bookmark, data)

    screen_xml = studio / "freeRDPCore/src/main/res/xml/screen_settings.xml"
    data = read(screen_xml)
    data = replace_once(data,
        '<PreferenceCategory android:title="@string/settings_cat_screen">',
        '''<PreferenceCategory
        android:key="bookmark.screen_category"
        android:title="@string/settings_cat_screen">
        <Preference
            android:key="bookmark.tv_display_guide"
            android:title="@string/settings_tv_display_recommended"
            android:summary="@string/settings_tv_display_recommended_summary"
            android:selectable="false" />''',
        "add TV display guide")
    data = replace_once(data,
        '<PreferenceCategory android:title="@string/settings_cat_scale">',
        '''<PreferenceCategory
        android:key="bookmark.scale_category"
        android:title="@string/settings_cat_scale">''',
        "add scale category key")
    write(screen_xml, data)

    dialogs = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/SessionDialogs.java"
    data = read(dialogs)
    data = replace_once(data, "import android.view.Gravity;\n",
                        "import android.view.Gravity;\nimport android.view.KeyEvent;\nimport android.view.inputmethod.EditorInfo;\nimport android.content.DialogInterface;\n",
                        "add credential focus imports")
    cred_end = '''\t\t                         .setCancelable(false)
\t\t                         .create();

\t\tdlgExperimental = new AlertDialog.Builder(activity)
'''
    cred_end_new = '''\t\t                         .setCancelable(false)
\t\t                         .create();

\t\tEditText credPassword = userCredView.findViewById(R.id.editTextPassword);
\t\tif (credPassword != null)
\t\t{
\t\t\tcredPassword.setSingleLine(true);
\t\t\tcredPassword.setImeOptions(EditorInfo.IME_ACTION_DONE);
\t\t\tcredPassword.setOnEditorActionListener((v, actionId, event) -> {
\t\t\t\tboolean enter = event != null &&
\t\t\t\t    event.getAction() == KeyEvent.ACTION_DOWN &&
\t\t\t\t    event.getKeyCode() == KeyEvent.KEYCODE_ENTER;
\t\t\t\tif (actionId == EditorInfo.IME_ACTION_DONE ||
\t\t\t\t    actionId == EditorInfo.IME_ACTION_GO || enter)
\t\t\t\t{
\t\t\t\t\tif (dlgUserCredentials.isShowing())
\t\t\t\t\t\tdlgUserCredentials.getButton(DialogInterface.BUTTON_POSITIVE).performClick();
\t\t\t\t\treturn true;
\t\t\t\t}
\t\t\t\treturn false;
\t\t\t});
\t\t\tcredPassword.setOnKeyListener((v, keyCode, event) -> {
\t\t\t\tif (DeviceMode.isTv(activity) &&
\t\t\t\t    keyCode == KeyEvent.KEYCODE_DPAD_DOWN &&
\t\t\t\t    event.getAction() == KeyEvent.ACTION_DOWN &&
\t\t\t\t    dlgUserCredentials.isShowing())
\t\t\t\t{
\t\t\t\t\tdlgUserCredentials.getButton(DialogInterface.BUTTON_POSITIVE).requestFocus();
\t\t\t\t\treturn true;
\t\t\t\t}
\t\t\t\treturn false;
\t\t\t});
\t\t}

\t\tdlgExperimental = new AlertDialog.Builder(activity)
'''
    data = replace_once(data, cred_end, cred_end_new,
                        "prefer Confirm after password entry")
    write(dialogs, data)

    en = studio / "freeRDPCore/src/main/res/values/strings.xml"
    data = read(en)
    en_add = '''
    <string name="settings_floating_toolbar">Remote-screen floating toolbar</string>
    <string name="settings_floating_toolbar_summary">Automatic hides it on TV and keeps it on phones/tablets.</string>
    <string-array name="floating_toolbar_entries">
        <item>Automatic (TV hidden / mobile shown)</item>
        <item>Always show</item>
        <item>Always hide</item>
    </string-array>
    <string-array name="floating_toolbar_values" translatable="false">
        <item>auto</item><item>show</item><item>hide</item>
    </string-array>
    <string name="settings_tv_display_recommended">Recommended TV display</string>
    <string name="settings_tv_display_recommended_summary">Use Automatic for full-screen large-display use. BILLION RDP REMOTE matches the remote desktop to the current TV viewport; no manual aspect-ratio calculation is normally needed.</string>
    <string-array name="tv_resolutions_array">
        <item>Automatic - match this TV (recommended)</item>
        <item>1920 × 1080 (Full HD 16:9)</item>
        <item>3840 × 2160 (4K 16:9)</item>
        <item>Custom</item>
    </string-array>
    <string-array name="tv_resolutions_values_array" translatable="false">
        <item>automatic</item>
        <item>1920x1080</item>
        <item>3840x2160</item>
        <item>custom</item>
    </string-array>
    <string name="settings_screen_summary_format">%1$s · %2$d-bit color</string>
'''
    data = insert_before_last(data, "</resources>", en_add,
                              "add Test9 English strings")
    write(en, data)

    zh = studio / "freeRDPCore/src/main/res/values-zh/strings.xml"
    data = read(zh)
    zh_add = '''
    <string name="settings_floating_toolbar">远程画面悬浮工具栏</string>
    <string name="settings_floating_toolbar_summary">自动模式下：电视隐藏，手机/平板显示。</string>
    <string-array name="floating_toolbar_entries">
        <item>自动（电视隐藏 / 手机显示，推荐）</item>
        <item>始终显示</item>
        <item>始终隐藏</item>
    </string-array>
    <string name="settings_tv_display_recommended">电视大屏推荐显示</string>
    <string name="settings_tv_display_recommended_summary">推荐选择“自动适配本机电视”。程序会按当前电视可用画面自动匹配远程桌面，不需要手工计算显示比例。</string>
    <string-array name="tv_resolutions_array">
        <item>自动适配本机电视（推荐）</item>
        <item>1920 × 1080（Full HD 16:9）</item>
        <item>3840 × 2160（4K 16:9）</item>
        <item>自定义</item>
    </string-array>
    <string name="settings_screen_summary_format">%1$s · %2$d 位色彩</string>
'''
    data = insert_before_last(data, "</resources>", zh_add,
                              "add Test9 Chinese strings")
    write(zh, data)

    print("Test9 patch applied:", VERSION)
    print("TV: no floating overlay by default, Confirm-first text dialogs, simplified display setup")
    print("Mobile/tablet: floating toolbar retained automatically and original display controls kept")

if __name__ == "__main__":
    main()
