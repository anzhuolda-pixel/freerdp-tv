package com.freerdp.freerdpcore.utils;

import android.content.Context;
import android.content.SharedPreferences;
import androidx.preference.PreferenceManager;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public final class BaihongEventLog
{
    private static final Object LOCK = new Object();
    private static final String DIR = "baihong-rdp-logs";
    private static final String KEY_RETENTION = "diagnostics.log_retention_days";
    private static final int DEFAULT_RETENTION_DAYS = 3;
    private static final int MAX_READ_LINES = 2500;

    private BaihongEventLog() {}

    public static int getRetentionDays(Context context)
    {
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(context);
        try
        {
            int value = Integer.parseInt(prefs.getString(KEY_RETENTION, "3"));
            return Math.max(1, Math.min(365, value));
        }
        catch (Throwable ignored)
        {
            return DEFAULT_RETENTION_DAYS;
        }
    }

    public static void log(Context context, String profile, String host, int port,
                           String event, String detail)
    {
        if (context == null) return;
        synchronized (LOCK)
        {
            try
            {
                File dir = new File(context.getFilesDir(), DIR);
                if (!dir.exists()) dir.mkdirs();
                cleanupLocked(context, dir);
                String day = new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date());
                File file = new File(dir, day + ".log");
                String time = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date());
                String endpoint = clean(host) + ":" + (port > 0 ? port : 3389);
                String line = time + " | " + clean(profile) + " | " + clean(event) + " | " +
                              endpoint + " | " + clean(detail) + "\n";
                try (FileOutputStream out = new FileOutputStream(file, true))
                {
                    out.write(line.getBytes(StandardCharsets.UTF_8));
                }
            }
            catch (Throwable ignored)
            {
                // Logging must never affect RDP stability.
            }
        }
    }

    public static String readRecent(Context context)
    {
        synchronized (LOCK)
        {
            try
            {
                File dir = new File(context.getFilesDir(), DIR);
                if (!dir.exists()) return "";
                cleanupLocked(context, dir);
                File[] files = dir.listFiles((d, name) -> name.endsWith(".log"));
                if (files == null || files.length == 0) return "";
                List<File> sorted = new ArrayList<>();
                Collections.addAll(sorted, files);
                sorted.sort((a, b) -> b.getName().compareTo(a.getName()));
                List<String> output = new ArrayList<>();
                for (File file : sorted)
                {
                    List<String> lines = new ArrayList<>();
                    try (BufferedReader reader = new BufferedReader(new InputStreamReader(
                             new FileInputStream(file), StandardCharsets.UTF_8)))
                    {
                        String line;
                        while ((line = reader.readLine()) != null) lines.add(line);
                    }
                    for (int i = lines.size() - 1; i >= 0; i--)
                    {
                        output.add(lines.get(i));
                        if (output.size() >= MAX_READ_LINES) break;
                    }
                    if (output.size() >= MAX_READ_LINES) break;
                }
                StringBuilder sb = new StringBuilder();
                for (String line : output) sb.append(line).append('\n');
                return sb.toString();
            }
            catch (Throwable ignored)
            {
                return "";
            }
        }
    }

    public static void clear(Context context)
    {
        synchronized (LOCK)
        {
            File dir = new File(context.getFilesDir(), DIR);
            File[] files = dir.listFiles();
            if (files == null) return;
            for (File file : files)
            {
                try { file.delete(); } catch (Throwable ignored) {}
            }
        }
    }

    private static void cleanupLocked(Context context, File dir)
    {
        long cutoff = System.currentTimeMillis() -
            getRetentionDays(context) * 24L * 60L * 60L * 1000L;
        File[] files = dir.listFiles((d, name) -> name.endsWith(".log"));
        if (files == null) return;
        for (File file : files)
        {
            if (file.lastModified() < cutoff)
            {
                try { file.delete(); } catch (Throwable ignored) {}
            }
        }
    }

    private static String clean(String value)
    {
        if (value == null) return "";
        String result = value.replace('\n', ' ').replace('\r', ' ').replace('|', '/').trim();
        return result.length() > 240 ? result.substring(0, 240) : result;
    }
}
