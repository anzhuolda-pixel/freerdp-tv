#!/usr/bin/env python3
import re
import sys
from pathlib import Path

VERSION = "3.31.1-baihong-konka32-api28-test21"
VERSION_CODE = "331121"


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
        fail("usage: patch_auto_reconnect_test21.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"

    props = studio / "release.properties"
    data = read(props)
    data = re.sub(r'^VERSION_NAME=.*$', 'VERSION_NAME=' + VERSION, data, count=1, flags=re.M)
    data = re.sub(r'^VERSION_CODE=.*$', 'VERSION_CODE=' + VERSION_CODE, data, count=1, flags=re.M)
    write(props, data)

    session = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/SessionActivity.java"
    data = read(session)

    data = replace_once(
        data,
        'import android.net.Uri;\n',
        'import android.net.ConnectivityManager;\nimport android.net.Network;\nimport android.net.NetworkInfo;\nimport android.net.Uri;\n',
        'add reconnect network imports')

    field_anchor = '\tprivate boolean failureDialogShown = false;\n'
    fields = '''\tprivate boolean failureDialogShown = false;\n\tprivate static final long[] AUTO_RECONNECT_DELAYS_MS = { 3000L, 5000L, 10000L, 20000L, 30000L };\n\tprivate final Handler reconnectHandler = new Handler(Looper.getMainLooper());\n\tprivate final Runnable reconnectRunnable = () -> performAutoReconnect();\n\tprivate BookmarkBase reconnectBookmark = null;\n\tprivate int reconnectAttempt = 0;\n\tprivate boolean reconnectScheduled = false;\n\tprivate boolean reconnectNoticeShown = false;\n\tprivate boolean autoReconnectMode = false;\n\tprivate ConnectivityManager.NetworkCallback reconnectNetworkCallback = null;\n'''
    data = replace_once(data, field_anchor, fields, 'add reconnect state fields')

    data = replace_once(
        data,
        '\t\tsuper.onCreate(savedInstanceState);\n',
        '\t\tsuper.onCreate(savedInstanceState);\n\t\tregisterReconnectNetworkCallback();\n',
        'register network callback')

    data = replace_once(
        data,
        '\t\tsuper.onDestroy();\n',
        '\t\treconnectHandler.removeCallbacksAndMessages(null);\n\t\tunregisterReconnectNetworkCallback();\n\t\tsuper.onDestroy();\n',
        'cleanup reconnect callback')

    connect_anchor = '''\tprivate void connect(BookmarkBase bookmark)\n\t{\n\t\tsession = GlobalApp.createSession(bookmark, getApplicationContext());\n'''
    connect_new = '''\tprivate void connect(BookmarkBase bookmark)\n\t{\n\t\treconnectBookmark = bookmark;\n\t\tsession = GlobalApp.createSession(bookmark, getApplicationContext());\n'''
    data = replace_once(data, connect_anchor, connect_new, 'remember bookmark for reconnect')

    back_anchor = '''\tpublic void handleBackPressed()\n\t{\n\t\t// hide keyboards (if any visible) or send alt+f4 to the session\n'''
    back_new = '''\tpublic void handleBackPressed()\n\t{\n\t\tif (autoReconnectMode)\n\t\t{\n\t\t\tconnectCancelledByUser = true;\n\t\t\tautoReconnectMode = false;\n\t\t\treconnectScheduled = false;\n\t\t\treconnectHandler.removeCallbacks(reconnectRunnable);\n\t\t\tcloseSessionActivity(RESULT_CANCELED);\n\t\t\treturn;\n\t\t}\n\n\t\t// hide keyboards (if any visible) or send alt+f4 to the session\n'''
    data = replace_once(data, back_anchor, back_new, 'allow Back to cancel reconnect loop')

    connected_anchor = '''\tprivate void onSessionConnected()\n\t{\n\t\tLog.v(TAG, "onSessionConnected");\n'''
    connected_new = '''\tprivate void onSessionConnected()\n\t{\n\t\tLog.v(TAG, "onSessionConnected");\n\t\treconnectHandler.removeCallbacks(reconnectRunnable);\n\t\treconnectScheduled = false;\n\t\treconnectAttempt = 0;\n\t\treconnectNoticeShown = false;\n\t\tautoReconnectMode = false;\n\t\tfailureDialogShown = false;\n'''
    data = replace_once(data, connected_anchor, connected_new, 'reset reconnect state after success')

    data = replace_once(data, '\tprivate void onSessionFailed()\n',
                        '\tprivate void onSessionFailedFinal()\n',
                        'preserve original permanent failure handler')
    data = replace_once(data, '\tprivate void onSessionDisconnected()\n',
                        '\tprivate void onSessionDisconnectedFinal()\n',
                        'preserve original user disconnect handler')

    state_anchor = '\tprivate void onConnectionStateChanged(SessionViewModel.ConnectionState state)\n'
    helpers = r'''	private boolean isNetworkReadyForReconnect()
	{
		try
		{
			ConnectivityManager cm =
			    (ConnectivityManager)getSystemService(Context.CONNECTIVITY_SERVICE);
			if (cm == null)
				return true;
			NetworkInfo info = cm.getActiveNetworkInfo();
			return info != null && info.isConnected();
		}
		catch (Throwable t)
		{
			// Vendor Android TV firmware occasionally has incomplete connectivity
			// services. In that case, attempt RDP instead of becoming stuck forever.
			Log.w(TAG, "Unable to query network state; allowing reconnect attempt", t);
			return true;
		}
	}

	private boolean isPermanentConnectionFailure()
	{
		if (session == null)
			return false;
		String raw = LibFreeRDP.getLastErrorString(session.getInstance());
		if (raw == null)
			return false;
		String value = raw.toLowerCase(java.util.Locale.US);
		return value.contains("logon") || value.contains("password") ||
		       value.contains("credential") || value.contains("authentication") ||
		       value.contains("account locked") || value.contains("account disabled") ||
		       value.contains("account expired") || value.contains("access denied") ||
		       value.contains("certificate rejected") || value.contains("certificate changed");
	}

	private void registerReconnectNetworkCallback()
	{
		try
		{
			ConnectivityManager cm =
			    (ConnectivityManager)getSystemService(Context.CONNECTIVITY_SERVICE);
			if (cm == null || reconnectNetworkCallback != null)
				return;
			reconnectNetworkCallback = new ConnectivityManager.NetworkCallback() {
				@Override public void onAvailable(Network network)
				{
					reconnectHandler.post(() -> {
						if (!autoReconnectMode || !reconnectScheduled ||
						    reconnectBookmark == null || connectCancelledByUser)
							return;
						reconnectHandler.removeCallbacks(reconnectRunnable);
						reconnectScheduled = true;
						reconnectHandler.postDelayed(reconnectRunnable, 1000L);
					});
				}
			};
			cm.registerDefaultNetworkCallback(reconnectNetworkCallback);
		}
		catch (Throwable t)
		{
			Log.w(TAG, "Network callback unavailable; timed reconnect remains active", t);
			reconnectNetworkCallback = null;
		}
	}

	private void unregisterReconnectNetworkCallback()
	{
		if (reconnectNetworkCallback == null)
			return;
		try
		{
			ConnectivityManager cm =
			    (ConnectivityManager)getSystemService(Context.CONNECTIVITY_SERVICE);
			if (cm != null)
				cm.unregisterNetworkCallback(reconnectNetworkCallback);
		}
		catch (Throwable t)
		{
			Log.w(TAG, "Ignoring network callback cleanup failure", t);
		}
		reconnectNetworkCallback = null;
	}

	private void scheduleAutoReconnect()
	{
		if (connectCancelledByUser || reconnectBookmark == null || isFinishing())
			return;

		autoReconnectMode = true;
		dialogs.dismissProgress();
		if (inputManager != null)
			inputManager.cancelPendingEvents();
		if (railManager != null)
			railManager.clear();
		if (session != null)
			session.setUIEventListener(null);
		if (DeviceMode.isTv(this))
			getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

		int index = Math.min(reconnectAttempt, AUTO_RECONNECT_DELAYS_MS.length - 1);
		long delay = AUTO_RECONNECT_DELAYS_MS[index];
		if (!isNetworkReadyForReconnect())
			delay = Math.max(delay, 5000L);

		reconnectHandler.removeCallbacks(reconnectRunnable);
		reconnectScheduled = true;
		if (!reconnectNoticeShown)
		{
			Toast.makeText(this, R.string.session_auto_reconnect_wait, Toast.LENGTH_LONG).show();
			reconnectNoticeShown = true;
		}
		reconnectHandler.postDelayed(reconnectRunnable, delay);
		Log.i(TAG, "Auto reconnect scheduled in " + delay + " ms, attempt=" + reconnectAttempt);
	}

	private void performAutoReconnect()
	{
		reconnectScheduled = false;
		if (!autoReconnectMode || connectCancelledByUser || reconnectBookmark == null ||
		    isFinishing())
			return;

		if (!isNetworkReadyForReconnect())
		{
			reconnectAttempt = Math.min(reconnectAttempt + 1, AUTO_RECONNECT_DELAYS_MS.length - 1);
			scheduleAutoReconnect();
			return;
		}

		if (connectThread != null && connectThread.isAlive())
		{
			scheduleAutoReconnect();
			return;
		}

		if (session != null)
		{
			long oldInstance = session.getInstance();
			try
			{
				session.setUIEventListener(null);
				sessionViewModel.unregister();
				GlobalApp.freeSession(oldInstance);
			}
			catch (Throwable t)
			{
				Log.w(TAG, "Failed to fully release old RDP instance before reconnect", t);
			}
			session = null;
		}

		failureDialogShown = false;
		reconnectAttempt = Math.min(reconnectAttempt + 1, AUTO_RECONNECT_DELAYS_MS.length - 1);
		Log.i(TAG, "Attempting automatic RDP reconnect, attempt=" + reconnectAttempt);
		connect(reconnectBookmark);
	}

	private void onSessionFailed()
	{
		if (connectCancelledByUser || reconnectBookmark == null || isPermanentConnectionFailure())
		{
			autoReconnectMode = false;
			reconnectScheduled = false;
			reconnectHandler.removeCallbacks(reconnectRunnable);
			onSessionFailedFinal();
			return;
		}

		Log.w(TAG, "Transient RDP connection failure; keeping activity alive for auto reconnect");
		scheduleAutoReconnect();
	}

	private void onSessionDisconnected()
	{
		if (connectCancelledByUser || reconnectBookmark == null)
		{
			autoReconnectMode = false;
			reconnectScheduled = false;
			reconnectHandler.removeCallbacks(reconnectRunnable);
			onSessionDisconnectedFinal();
			return;
		}

		Log.w(TAG, "RDP session disconnected unexpectedly; starting auto reconnect loop");
		scheduleAutoReconnect();
	}

'''
    data = replace_once(data, state_anchor, helpers + state_anchor,
                        'insert automatic reconnect controller')
    write(session, data)

    en = studio / "freeRDPCore/src/main/res/values/strings.xml"
    data = read(en)
    data = insert_before_last(
        data,
        '</resources>',
        '    <string name="session_auto_reconnect_wait">Remote connection interrupted. Waiting for the network/server and reconnecting automatically…</string>\n',
        'add English reconnect status')
    write(en, data)

    zh = studio / "freeRDPCore/src/main/res/values-zh/strings.xml"
    data = read(zh)
    data = insert_before_last(
        data,
        '</resources>',
        '    <string name="session_auto_reconnect_wait">远程连接已中断，正在等待网络或服务器恢复，并自动重新连接…</string>\n',
        'add Chinese reconnect status')
    write(zh, data)

    final = read(session)
    checks = [
        'AUTO_RECONNECT_DELAYS_MS',
        'registerDefaultNetworkCallback',
        'performAutoReconnect()',
        'private void onSessionFailedFinal()',
        'private void onSessionDisconnectedFinal()',
        'private void onSessionFailed()',
        'private void onSessionDisconnected()',
        'R.string.session_auto_reconnect_wait',
    ]
    for marker in checks:
        if marker not in final:
            fail('missing reconnect marker: ' + marker)
    if 'VERSION_NAME=' + VERSION not in read(props):
        fail('Test21 version name missing')

    print('Test21 patch applied: resilient RDP auto reconnect enabled')
    print('Backoff: 3/5/10/20/30 seconds, then 30 seconds indefinitely')
    print('Network restoration callback accelerates retry; account/auth failures do not loop')


if __name__ == '__main__':
    main()
