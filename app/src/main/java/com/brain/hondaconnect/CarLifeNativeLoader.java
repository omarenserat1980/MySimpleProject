package com.brain.hondaconnect;

import android.content.Context;
import android.os.Build;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;

/** Extracts the pinned CarLife runtime and loads dependencies in SONAME order. */
final class CarLifeNativeLoader {
    private static boolean loaded;
    private static String failure = "";
    private static final String[] LIBRARIES = {
        "libc++_shared.so",
        "libz.so.1",
        "libiconv.so",
        "libicudata.so.78",
        "libicuuc.so.78",
        "libxml2.so.16",
        "libcarlifevehicle.so"
    };

    static synchronized boolean load(Context context) {
        if (loaded) return true;
        if (!Build.SUPPORTED_ABIS[0].equals("arm64-v8a")) {
            failure = "هذه الحزمة تحتوي مكتبات arm64-v8a فقط";
            return false;
        }
        File dir = new File(context.getFilesDir(), "carlife-native/arm64-v8a");
        if (!dir.exists() && !dir.mkdirs()) {
            failure = "تعذر إنشاء مجلد مكتبات CarLife";
            return false;
        }
        try {
            for (String name : LIBRARIES) {
                File target = new File(dir, name);
                if (!target.isFile() || target.length() == 0) {
                    try (InputStream in = context.getAssets().open("carlife-native/arm64-v8a/" + name);
                         FileOutputStream out = new FileOutputStream(target)) {
                        byte[] buffer = new byte[64 * 1024];
                        int count;
                        while ((count = in.read(buffer)) != -1) out.write(buffer, 0, count);
                    }
                    target.setReadable(true, true);
                    target.setExecutable(true, true);
                }
                System.load(target.getAbsolutePath());
            }
            loaded = true;
            return true;
        } catch (Throwable error) {
            failure = error.getClass().getSimpleName() + ": " + error.getMessage();
            return false;
        }
    }

    static synchronized String error() { return failure; }
    private CarLifeNativeLoader() {}
}
