package com.electronicbrain.androidexecutor

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

enum class QueueState { PENDING, RUNNING, SUCCEEDED, FAILED, VERIFIED }

data class QueueItem(
    val id: String = UUID.randomUUID().toString(),
    val task: String,
    val args: JSONObject = JSONObject(),
    var state: QueueState = QueueState.PENDING,
    var attempt: Int = 0,
    var lastError: String = "",
    var output: String = "",
    var updatedAt: Long = System.currentTimeMillis()
)

class QueueStore(context: Context) {
    private val file = File(context.filesDir, "executor-queue.json")
    private val lock = Any()

    fun load(): MutableList<QueueItem> = synchronized(lock) {
        if (!file.exists()) return mutableListOf()
        val arr = JSONArray(file.readText())
        MutableList(arr.length()) { i ->
            val o = arr.getJSONObject(i)
            QueueItem(
                id=o.optString("id"), task=o.optString("task"),
                args=o.optJSONObject("args") ?: JSONObject(),
                state=runCatching { QueueState.valueOf(o.optString("state")) }.getOrDefault(QueueState.PENDING),
                attempt=o.optInt("attempt"), lastError=o.optString("lastError"),
                output=o.optString("output"), updatedAt=o.optLong("updatedAt")
            )
        }
    }

    fun save(items: List<QueueItem>) = synchronized(lock) {
        val arr = JSONArray()
        items.forEach { q ->
            arr.put(JSONObject().apply {
                put("id",q.id); put("task",q.task); put("args",q.args)
                put("state",q.state.name); put("attempt",q.attempt)
                put("lastError",q.lastError); put("output",q.output)
                put("updatedAt",q.updatedAt)
            })
        }
        file.writeText(arr.toString())
    }

    fun enqueue(task: String, args: JSONObject = JSONObject()): QueueItem {
        val q=QueueItem(task=task,args=args)
        val all=load(); all.add(q); save(all); return q
    }

    fun recoverRunning() {
        val all=load(); var changed=false
        all.forEach { if (it.state==QueueState.RUNNING) { it.state=QueueState.PENDING; it.updatedAt=System.currentTimeMillis(); changed=true } }
        if(changed) save(all)
    }
}
