package com.electronicbrain.androidexecutor

import org.json.JSONObject
import java.io.File

class ProductionTasks(private val context:android.content.Context){
    private val ffmpeg=FFmpegEngine(context)
    fun execute(task:String,args:JSONObject):Map<String,Any>{
        return when(task){
            "scene_prepare" -> {
                val dir=File(args.getString("scene_dir")).canonicalFile
                dir.mkdirs()
                mapOf("ok" to true,"scene_dir" to dir.absolutePath)
            }
            "concat_video" -> {
                val argv=args.getJSONArray("argv")
                val list=List(argv.length()){i->argv.getString(i)}
                ffmpeg.run(list)
            }
            "verify_output" -> {
                val f=File(args.getString("path")).canonicalFile
                VerificationEngine.file(f,args.optLong("min_bytes",1024))
            }
            else -> mapOf("ok" to false,"error" to "UNKNOWN_PRODUCTION_TASK")
        }
    }
}
