package com.electronicbrain.androidexecutor

data class BrainCapability(
    val id: String,
    val name: String,
    val state: State = State.UNKNOWN,
    val detail: String = ""
) {
    enum class State { READY, DEGRADED, BLOCKED, UNKNOWN }
}

data class BrainDecision(
    val action: String,
    val reason: String,
    val requiresPermission: Boolean = false
)

class BrainCortex {
    private val capabilities = linkedMapOf(
        "gateway" to BrainCapability("gateway", "Brain Gateway"),
        "termux" to BrainCapability("termux", "Termux"),
        "accessibility" to BrainCapability("accessibility", "Accessibility"),
        "storage" to BrainCapability("storage", "Storage"),
        "executor" to BrainCapability("executor", "Android Executor", BrainCapability.State.READY)
    )

    fun snapshot(): List<BrainCapability> = capabilities.values.toList()

    fun decide(action: String, requiresPermission: Boolean = false): BrainDecision =
        BrainDecision(
            action = action,
            reason = "Cortex policy: observe -> decide -> permission -> execute -> verify",
            requiresPermission = requiresPermission
        )

    fun constitution(): List<String> = listOf(
        "No sensitive action without an explicit permission gate.",
        "No success claim without verification evidence.",
        "Do not retry a failure blindly; diagnose first.",
        "Prefer one orchestrated execution path over competing loops.",
        "Keep recovery/rollback possible before system-changing operations."
    )
}
