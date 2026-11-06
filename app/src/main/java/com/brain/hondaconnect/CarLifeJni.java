package com.brain.hondaconnect;

/** JNI methods; loading is centralized in CarLifeNativeLoader. */
final class CarLifeJni {
    private CarLifeJni() {}

    static boolean loadBridge() {
        return CarLifeNativeLoader.load(null);
    }

    static String error() { return CarLifeNativeLoader.error(); }

    static native int nativeInitialize();
    static native int nativeConnectionSetup(String mdIp, String interfaceName);
    static native void nativeDisconnect();
}
