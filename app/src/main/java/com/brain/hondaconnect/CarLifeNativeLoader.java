package com.brain.hondaconnect;

import android.content.Context;
import android.os.Build;

/** Loads the JNI bridge; its native dependency closure is packaged beside it in lib/arm64-v8a. */
final class CarLifeNativeLoader {
    private static boolean loaded;
    private static String failure = "";

    static synchronized boolean load(Context context) {
        if (loaded) return true;
        if (!Build.SUPPORTED_ABIS[0].equals("arm64-v8a")) {
            failure = "هذه الحزمة تحتوي مكتبات arm64-v8a فقط";
            return false;
        }
        try {
            // Load the provider explicitly before the JNI consumer. This also
            // makes provider-load failures distinguishable from JNI failures.
            try {
                System.loadLibrary("carlifevehicle");
            } catch (Throwable error) {
                failure = "libcarlifevehicle load failed: "
                        + error.getClass().getSimpleName() + ": " + error.getMessage();
                android.util.Log.e("BrainCarLifeJNI", failure, error);
                return false;
            }
            try {
                System.loadLibrary("braincarlife_jni");
            } catch (Throwable error) {
                failure = "libbraincarlife_jni load failed: "
                        + error.getClass().getSimpleName() + ": " + error.getMessage();
                android.util.Log.e("BrainCarLifeJNI", failure, error);
                return false;
            }
            loaded = true;
            failure = "";
            return true;
        } catch (Throwable error) {
            failure = error.getClass().getSimpleName() + ": " + error.getMessage();
            android.util.Log.e("BrainCarLifeJNI", "Native dependency load failed", error);
            return false;
        }
    }

    static synchronized String error() { return failure; }
    private CarLifeNativeLoader() {}
}
