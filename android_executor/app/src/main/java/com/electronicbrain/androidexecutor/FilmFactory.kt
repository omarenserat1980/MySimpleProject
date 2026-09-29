package com.electronicbrain.androidexecutor

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

class FilmFactory(private val context: Context) {
    private val projects = FilmProjectStore(context)
    private val queue = QueueStore(context)

    fun createProduction(title: String, durationSec: Int = 60, sceneCount: Int = 4): File {
        require(sceneCount > 0)
        require(durationSec >= sceneCount)
        val dir = projects.create(title, durationSec)
        val base = durationSec / sceneCount
        val remainder = durationSec % sceneCount
        for (i in 1..sceneCount) {
            val sceneId = "scene-%03d".format(i)
            val sceneDir = File(dir, "scenes/$sceneId").apply { mkdirs() }
            val duration = base + if (i == sceneCount) remainder else 0
            projects.addScene(dir, FilmScene(sceneId, i, "Scene $i", duration))
            queue.enqueue("scene_prepare", JSONObject().apply {
                put("project_dir", dir.absolutePath)
                put("scene_id", sceneId)
                put("scene_dir", sceneDir.absolutePath)
            })
        }
        writeManifest(dir, title, durationSec, sceneCount)
        return dir
    }

    fun createCinematicFilm(title: String, durationSec: Int = 60, sceneCount: Int = 8): File {
        val dir = createProduction(title, durationSec, sceneCount)
        val plan = JSONObject().apply {
            put("pipeline", JSONArray(listOf(
                "STORY", "CHARACTERS", "WORLD", "SHOTS", "IMAGE", "AUDIO",
                "VIDEO", "QUALITY", "MASTER"
            )))
            put("status", "PLANNED")
            put("automatic_resume", true)
            put("created_at", System.currentTimeMillis())
        }
        File(dir, "cinematic_plan.json").writeText(plan.toString(2))
        queue.enqueue("cinematic_plan", JSONObject().put("project_dir", dir.absolutePath))
        return dir
    }

    private fun writeManifest(dir: File, title: String, durationSec: Int, sceneCount: Int) {
        File(dir, "factory_manifest.json").writeText(JSONObject().apply {
            put("schema", "electronic-brain-film-factory-v2")
            put("id", UUID.randomUUID().toString())
            put("title", title)
            put("duration_sec", durationSec)
            put("scene_count", sceneCount)
            put("root", dir.absolutePath)
            put("status", "QUEUED")
        }.toString(2))
    }
}
