package com.electronicbrain.androidexecutor

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Bundle

class TermuxResultReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val executionId = intent.getIntExtra(TermuxBridge.EXTRA_EXECUTION_ID, 0)
        val bundle = intent.getBundleExtra(TermuxBridge.EXTRA_RESULT_BUNDLE) ?: Bundle()
        TermuxBridge.complete(executionId, bundle)
    }
}
