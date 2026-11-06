package com.brain.hondaconnect;

/** Narrow JNI boundary to the pinned CarLife MD C++ library. */
final class CarLifeJni {
    private static boolean bridgeLoaded;
    private CarLifeJni() {}

    static synchronized boolean loadBridge() {
        if (bridgeLoaded) return true;
        try {
            System.loadLibrary("braincarlife_jni");
            bridgeLoaded = true;
            return true;
        } catch (Throwable error) {
            return false;
        }
    }

    static native int nativeInitialize();
    static native int nativeConnectionSetup(String mdIp, String interfaceName);
    static native void nativeDisconnect();
}
