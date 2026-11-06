#include <jni.h>
#include <android/log.h>
#include <mutex>
#include <string>
#include <net/if.h>
#include <arpa/inet.h>
#include "CCarLifeLibWrapper.h"

#define TAG "BrainCarLifeJNI"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, TAG, __VA_ARGS__)

namespace {
std::mutex g_mutex;
bool g_initialized = false;
bool g_connection_attempted = false;
CCarLifeLibH::CCarLifeLib* instance() { return CCarLifeLibH::CCarLifeLib::getInstance(); }
}

extern "C" JNIEXPORT jint JNICALL
Java_com_brain_hondaconnect_CarLifeJni_nativeInitialize(JNIEnv*, jclass) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_initialized) return 0;
    auto* lib = instance();
    if (lib == nullptr) return -10;
    const int result = lib->carLifeLibInit();
    if (result == 0) {
        g_initialized = true;
        LOGI("CarLife library initialized; no transport/session started");
    }
    return result;
}

extern "C" JNIEXPORT jint JNICALL
Java_com_brain_hondaconnect_CarLifeJni_nativeConnectionSetup(JNIEnv* env, jclass,
                                                              jstring md_ip,
                                                              jstring interface_name) {
    if (md_ip == nullptr || interface_name == nullptr) return -20;
    const char* ip_chars = env->GetStringUTFChars(md_ip, nullptr);
    const char* iface_chars = env->GetStringUTFChars(interface_name, nullptr);
    if (ip_chars == nullptr || iface_chars == nullptr) {
        if (ip_chars) env->ReleaseStringUTFChars(md_ip, ip_chars);
        if (iface_chars) env->ReleaseStringUTFChars(interface_name, iface_chars);
        return -21;
    }
    const std::string ip(ip_chars), iface(iface_chars);
    env->ReleaseStringUTFChars(md_ip, ip_chars);
    env->ReleaseStringUTFChars(interface_name, iface_chars);

    in_addr parsed{};
    if (inet_pton(AF_INET, ip.c_str(), &parsed) != 1 || iface.empty() || iface.size() > IFNAMSIZ - 1) return -22;
    std::lock_guard<std::mutex> lock(g_mutex);
    if (!g_initialized || g_connection_attempted) return -23;
    g_connection_attempted = true;
    const int result = instance()->connectionSetup(ip, iface);
    LOGI("Explicit IP/interface connectionSetup returned %d", result);
    return result;
}

extern "C" JNIEXPORT void JNICALL
Java_com_brain_hondaconnect_CarLifeJni_nativeDisconnect(JNIEnv*, jclass) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_initialized) {
        instance()->disconnect();
        g_initialized = false;
        g_connection_attempted = false;
        LOGI("CarLife library disconnected/reset");
    }
}
