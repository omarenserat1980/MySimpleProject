package com.electronicbrain.androidexecutor

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

data class FilmScene(val id:String,val order:Int,val title:String,val durationSec:Int,val image:String="",val audio:String="",val video:String="")

class FilmProjectStore(private val context:Context){
    private val root=File("/storage/emulated/0/Movies/ElectronicBrain/films").apply{mkdirs()}
    fun create(title:String,durationSec:Int=60):File{
        val id=UUID.randomUUID().toString()
        val dir=File(root,id).apply{mkdirs()}
        val project=JSONObject().apply{
            put("schema","film-project-v1");put("id",id);put("title",title)
            put("duration_sec",durationSec);put("created_at",System.currentTimeMillis())
            put("scenes",JSONArray())
        }
        File(dir,"project.json").writeText(project.toString(2))
        return dir
    }
    fun addScene(dir:File,scene:FilmScene){
        val file=File(dir,"project.json")
        val p=JSONObject(file.readText());val a=p.optJSONArray("scenes")?:JSONArray()
        a.put(JSONObject().apply{put("id",scene.id);put("order",scene.order);put("title",scene.title);put("duration_sec",scene.durationSec);put("image",scene.image);put("audio",scene.audio);put("video",scene.video)})
        p.put("scenes",a);file.writeText(p.toString(2))
    }
}
