#!/usr/bin/env python3
import re, sys
from pathlib import Path

src = Path(sys.argv[1]).resolve()
studio = src / 'client' / 'Android' / 'Studio'
props = studio / 'release.properties'
s = props.read_text(encoding='utf-8')
for key, value in {
    'VERSION_NAME':'3.31.1-baihong-konka32-test18',
    'VERSION_CODE':'331118',
    'MIN_API':'28',
    'TARGET_API':'28',
    'ABI_FILTERS':'armeabi-v7a',
    'SPLIT_ARCHITECTURES':'armeabi-v7a',
    'SPLIT_ENABLED':'false',
    'BUILD_UNIVERSAL':'true',
}.items():
    pat = re.compile(r'^' + re.escape(key) + r'=.*$', re.M)
    if pat.search(s):
        s = pat.sub(key + '=' + value, s, count=1)
    else:
        s += '\n' + key + '=' + value
props.write_text(s + ('\n' if not s.endswith('\n') else ''), encoding='utf-8')

# Use standard Room/SQLite for this TV-only compatibility build.
appdb = studio / 'freeRDPCore/src/main/java/com/freerdp/freerdpcore/data/AppDatabase.java'
appdb.write_text('''package com.freerdp.freerdpcore.data;\n\nimport android.content.Context;\nimport androidx.room.Database;\nimport androidx.room.Room;\nimport androidx.room.RoomDatabase;\n\n@Database(entities = { BookmarkEntity.class }, version = 18, exportSchema = false)\npublic abstract class AppDatabase extends RoomDatabase {\n    private static volatile AppDatabase instance;\n    public abstract BookmarkDao bookmarkDao();\n    public static AppDatabase getInstance(Context context) {\n        if (instance == null) {\n            synchronized (AppDatabase.class) {\n                if (instance == null) {\n                    instance = Room.databaseBuilder(context.getApplicationContext(), AppDatabase.class, "bookmarks_konka32.db")\n                        .fallbackToDestructiveMigration()\n                        .build();\n                }\n            }\n        }\n        return instance;\n    }\n}\n''', encoding='utf-8')

core = studio / 'freeRDPCore/build.gradle'
g = core.read_text(encoding='utf-8')
g = re.sub(r"androidx\.core:core:[^']+", 'androidx.core:core:1.10.1', g)
g = re.sub(r"androidx\.recyclerview:recyclerview:[^']+", 'androidx.recyclerview:recyclerview:1.3.2', g)
g = re.sub(r'androidx\.room:room-runtime:[^"]+', 'androidx.room:room-runtime:2.5.2', g)
g = re.sub(r'androidx\.room:room-compiler:[^"]+', 'androidx.room:room-compiler:2.5.2', g)
g, removed = re.subn(r'(?m)^\s*implementation\s+[\'\"]net\.zetetic:sqlcipher-android:[^\'\"]+[\'\"]\s*\n?', '', g, count=1)
if removed != 1:
    raise SystemExit('Test18 patch error: expected exactly one SQLCipher dependency line')
g = re.sub(r"androidx\.sqlite:sqlite:[^']+", 'androidx.sqlite:sqlite:2.3.1', g)
if 'sqlcipher-android' in g:
    raise SystemExit('Test18 patch error: SQLCipher dependency still present')
core.write_text(g, encoding='utf-8')

home = studio / 'freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/HomeActivity.java'
h = home.read_text(encoding='utf-8')
h = h.replace('\t\tAppKeepAliveService.applyPreference(this);\n', '\t\tbinding.getRoot().postDelayed(() -> AppKeepAliveService.applyPreference(HomeActivity.this), 5000L);\n', 1)
home.write_text(h, encoding='utf-8')

print('Test18 Konka32 patch applied - SQLCipher removed, armeabi-v7a only')
