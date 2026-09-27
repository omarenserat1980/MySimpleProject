package com.electronicbrain.androidexecutor

import android.content.Context
import org.json.JSONObject
import java.io.File

class QueueWorker(private val context: Context) {
    private val store=QueueStore(context)
    private val ffmpeg=FFmpegEngine(context)

    fun resumeOnce() {
        store.recoverRunning()
        val items=store.load()
        val q=items.firstOrNull { it.state==QueueState.PENDING } ?: return
        q.state=QueueState.RUNNING; q.attempt++; q.updatedAt=System.currentTimeMillis(); store.save(items)
        try {
            val result=when(q.task) {
                "ffmpeg_probe" -> ffmpeg.probe()
                "ffmpeg_run" -> ffmpeg.run(jsonArgs(q.args))
                "verify_file" -> verify(q.args)
                "scene_prepare" -> ProductionTasks(context).execute(q.task,q.args)
                "concat_video" -> ProductionTasks(context).execute(q.task,q.args)
                "verify_output" -> ProductionTasks(context).execute(q.task,q.args)
                else -> mapOf("ok" to false,"error" to ("unsupported queued task: " + q.task))
            }
            q.output=JSONObject(result).toString()
            val ok=result["ok"]==true || result["available"]==true || (result["exists"]==true && result["size_ok"]==true)
            q.state=if(ok) QueueState.SUCCEEDED else QueueState.FAILED
            q.lastError=if(ok) "" else result["error"]?.toString() ?: result["stderr"]?.toString() ?: "failed"
        } catch(e:Throwable) {
            q.state=QueueState.FAILED; q.lastError=e.message ?: e.javaClass.simpleName
        } finally { q.updatedAt=System.currentTimeMillis(); store.save(items) }
    }

    private fun jsonArgs(o: JSONObject): List<String> {
        val a=o.optJSONArray("argv") ?: throw IllegalArgumentException("argv missing")
        return List(a.length()) { i -> a.getString(i) }
    }

    private fun verify(o: JSONObject): Map<String,Any> {
        val p=o.optString("path")
        require(p.isNotBlank())
        val f=File(p).canonicalFile
        val root=File("/storage/emulated/0/Movies/ElectronicBrain").canonicalFile
        require(f.path.startsWith(root.path+File.separator)) { "path outside factory root" }
        return VerificationEngine.file(f,o.optLong("min_bytes",1L))
    }
}
