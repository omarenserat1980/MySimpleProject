package com.electronicbrain.androidexecutor

import android.content.Context
import org.json.JSONObject
import java.io.File

class FilmFactory(private val context:Context){
    private val projects=FilmProjectStore(context)
    private val queue=QueueStore(context)

    fun createProduction(title:String,durationSec:Int=60,sceneCount:Int=4):File{
        require(sceneCount>0)
        val dir=projects.create(title,durationSec)
        val per=(durationSec/sceneCount).coerceAtLeast(1)
        for(i in 1..sceneCount){
            val sceneId="scene-%03d".format(i)
            val sceneDir=File(dir,"scenes/$sceneId").apply{mkdirs()}
            projects.addScene(dir,FilmScene(sceneId,i,"Scene $i",per))
            queue.enqueue("scene_prepare",JSONObject().apply{
                put("project_dir",dir.absolutePath);put("scene_id",sceneId);put("scene_dir",sceneDir.absolutePath)
            })
        }
        return dir
    }
}
