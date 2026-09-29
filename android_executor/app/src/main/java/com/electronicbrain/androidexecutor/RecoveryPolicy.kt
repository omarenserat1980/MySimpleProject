package com.electronicbrain.androidexecutor

object RecoveryPolicy {
    fun backoff(attempt: Int): Long = when {
        attempt <= 0 -> 1000L
        attempt == 1 -> 2000L
        attempt == 2 -> 5000L
        attempt == 3 -> 10000L
        else -> 30000L
    }

    fun shouldRetry(attempt: Int, maxAttempts: Int = 4): Boolean = attempt < maxAttempts
}
