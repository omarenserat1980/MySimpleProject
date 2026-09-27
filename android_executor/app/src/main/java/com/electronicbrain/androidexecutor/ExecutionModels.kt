package com.electronicbrain.androidexecutor

data class ExecutionRecord(
    val taskId: String,
    val task: String,
    val startedAt: Long,
    val finishedAt: Long,
    val ok: Boolean,
    val error: String = ""
)

object TaskPolicy {
    val allowedTasks = setOf(
        "status","device_info","platform","list_files","mkdir","read_file","write_text",
        "run_toybox","ffmpeg_probe","ffmpeg_run","verify_file","queue_status"
    )
}
