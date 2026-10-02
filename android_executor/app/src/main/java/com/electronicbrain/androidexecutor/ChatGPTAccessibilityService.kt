package com.electronicbrain.androidexecutor

import android.accessibilityservice.AccessibilityService
import android.os.Bundle
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import org.json.JSONObject

class ChatGPTAccessibilityService : AccessibilityService() {
    companion object {
        const val TARGET_PACKAGE = "com.openai.chatgpt"
        @Volatile var instance: ChatGPTAccessibilityService? = null
    }

    override fun onServiceConnected() { super.onServiceConnected(); instance = this }
    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() { instance = null }

    fun execute(message: String, timeoutMs: Long = 120_000L): JSONObject {
        if (message.isBlank()) return fail("EMPTY_MESSAGE")
        if (rootInActiveWindow?.packageName?.toString() != TARGET_PACKAGE)
            return fail("CHATGPT_APP_NOT_ACTIVE")
        val field = findEditable(rootInActiveWindow ?: return fail("NO_WINDOW"))
            ?: return fail("CHATGPT_INPUT_NOT_FOUND")
        val args = Bundle().apply {
            putCharSequence(
                AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, message
            )
        }
        if (!field.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args))
            return fail("TYPE_FAILED")
        val send = findSendNode(rootInActiveWindow ?: return fail("NO_WINDOW"))
            ?: return fail("SEND_BUTTON_NOT_FOUND")
        if (!send.performAction(AccessibilityNodeInfo.ACTION_CLICK))
            return fail("SEND_CLICK_FAILED")

        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            Thread.sleep(500)
            val current = rootInActiveWindow ?: continue
            val response = findLatestText(current)
            if (response.isNotBlank() && response != message) {
                return JSONObject()
                    .put("ok", true)
                    .put("ui_clicked", true)
                    .put("response_text", response)
                    .put("status", "UI_CONVERSATION_VERIFIED")
            }
        }
        return JSONObject().put("ok", false).put("ui_clicked", true)
            .put("error", "RESPONSE_TIMEOUT")
    }

    private fun findEditable(n: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        if (n.isEditable && n.isVisibleToUser) return n
        for (i in 0 until n.childCount)
            n.getChild(i)?.let { findEditable(it)?.let { x -> return x } }
        return null
    }

    private fun findSendNode(n: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        val t = n.text?.toString()?.trim().orEmpty()
        val d = n.contentDescription?.toString()?.trim().orEmpty()
        if (n.isVisibleToUser && n.isClickable &&
            (t.equals("Send", true) || d.equals("Send", true) ||
             t.equals("إرسال", true) || d.equals("إرسال", true))) return n
        for (i in 0 until n.childCount)
            n.getChild(i)?.let { findSendNode(it)?.let { x -> return x } }
        return null
    }

    private fun findLatestText(n: AccessibilityNodeInfo): String {
        val values = mutableListOf<String>()
        collect(n, values)
        return values.asReversed().firstOrNull { it.length >= 2 } ?: ""
    }

    private fun collect(n: AccessibilityNodeInfo, out: MutableList<String>) {
        n.text?.toString()?.trim()?.takeIf { it.isNotBlank() }?.let(out::add)
        for (i in 0 until n.childCount) n.getChild(i)?.let { collect(it, out) }
    }

    private fun fail(error: String) = JSONObject().put("ok", false).put("error", error)
}