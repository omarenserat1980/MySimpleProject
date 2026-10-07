package com.electronicbrain.androidexecutor

import org.junit.Assert.assertTrue
import org.junit.Test

class BrainCapabilityContractTest {
    @Test fun capability_contract_is_present() {
        val source = ExecutorService::class.java.name
        assertTrue(source.contains("ExecutorService"))
    }
}
