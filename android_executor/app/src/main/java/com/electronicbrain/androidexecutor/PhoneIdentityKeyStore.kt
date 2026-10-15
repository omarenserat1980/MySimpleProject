package com.electronicbrain.androidexecutor

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import org.json.JSONObject
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.Signature
import java.security.cert.Certificate
import java.security.spec.ECGenParameterSpec
import java.util.Base64

/**
 * Local-only Android Keystore identity helper.
 *
 * It never sends data anywhere and never activates/registers a node. A returned
 * certificate chain is evidence for an independent verifier; this class does
 * not claim that attestation is valid.
 */
object PhoneIdentityKeyStore {
    private const val ANDROID_KEY_STORE = "AndroidKeyStore"
    private const val KEY_ALIAS = "brain-phone-identity-p256-v1"

    data class EnrollmentMaterial(
        val keyId: String,
        val publicKeyPem: String,
        val attestationChainPem: List<String>,
        val attestationChallengeSha256: String,
        val signatureAlgorithm: String = "SHA256withECDSA",
        val attestationVerification: String = "NOT_PERFORMED",
        val deviceIdentityVerified: Boolean = false
    )

    data class SignedResponse(
        val payloadJson: String,
        val signatureBase64: String,
        val signatureAlgorithm: String = "SHA256withECDSA",
        val deviceIdentityVerified: Boolean = false
    )

    /** Read-only capability probe: does not generate or alter a key. */
    fun probeCapabilities(context: Context): Map<String, Any> {
        val providerAvailable = runCatching {
            KeyStore.getInstance(ANDROID_KEY_STORE).apply { load(null) }
        }.isSuccess
        val p256GeneratorAvailable = runCatching {
            KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, ANDROID_KEY_STORE)
        }.isSuccess
        val strongBoxAdvertised = Build.VERSION.SDK_INT >= Build.VERSION_CODES.P &&
            context.packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)
        return mapOf(
            "schema" to "brain-phone-base.android-keystore-capabilities.v1",
            "android_api" to Build.VERSION.SDK_INT,
            "android_keystore_provider_available" to providerAvailable,
            "p256_key_generator_available" to p256GeneratorAvailable,
            "strongbox_feature_advertised" to strongBoxAdvertised,
            "attestation_tested" to false,
            "device_identity_verified" to false,
            "trusted" to false,
            "active" to false,
            "manual_approval" to "NOT_GRANTED",
            "mining" to "DISABLED",
            "network_upload" to false
        )
    }

    /**
     * Create a new P-256 signing key and request Android Key Attestation using
     * an independent enrollment challenge. Refuses to silently reuse a key.
     * Call only from a foreground user action after obtaining that challenge.
     */
    @Synchronized
    fun createEnrollmentKey(attestationChallenge: ByteArray): EnrollmentMaterial {
        require(attestationChallenge.size >= 32) {
            "ATTESTATION_CHALLENGE_MUST_BE_AT_LEAST_32_BYTES"
        }
        val store = KeyStore.getInstance(ANDROID_KEY_STORE).apply { load(null) }
        check(!store.containsAlias(KEY_ALIAS)) {
            "IDENTITY_KEY_ALREADY_EXISTS; do not overwrite it automatically"
        }

        val spec = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
        )
            .setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1"))
            .setDigests(KeyProperties.DIGEST_SHA256)
            .setAttestationChallenge(attestationChallenge)
            .build()

        val generator = KeyPairGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_EC,
            ANDROID_KEY_STORE
        )
        generator.initialize(spec)
        generator.generateKeyPair()

        val certificate = store.getCertificate(KEY_ALIAS)
            ?: error("ANDROID_KEYSTORE_CERTIFICATE_MISSING")
        val chain = store.getCertificateChain(KEY_ALIAS)
            ?: error("ANDROID_KEYSTORE_ATTESTATION_CHAIN_MISSING")
        check(chain.isNotEmpty()) { "ANDROID_KEYSTORE_ATTESTATION_CHAIN_EMPTY" }

        val publicKeyDer = certificate.publicKey.encoded
        return EnrollmentMaterial(
            keyId = sha256Hex(publicKeyDer),
            publicKeyPem = pem("PUBLIC KEY", publicKeyDer),
            attestationChainPem = chain.map { cert -> pemCertificate(cert) },
            attestationChallengeSha256 = sha256Hex(attestationChallenge)
        )
    }

    /** Sign a canonical response map with the non-exportable Keystore key. */
    @Synchronized
    fun signResponse(fields: Map<String, String>): SignedResponse {
        require(fields["schema"] == "brain-phone-base.identity-response.v1") {
            "IDENTITY_RESPONSE_SCHEMA_INVALID"
        }
        val store = KeyStore.getInstance(ANDROID_KEY_STORE).apply { load(null) }
        val privateKey = store.getKey(KEY_ALIAS, null)
            ?: error("ANDROID_IDENTITY_KEY_NOT_ENROLLED")
        val certificate = store.getCertificate(KEY_ALIAS)
            ?: error("ANDROID_IDENTITY_CERTIFICATE_MISSING")
        val expectedKeyId = sha256Hex(certificate.publicKey.encoded)
        require(fields["device_key_id"] == expectedKeyId) {
            "IDENTITY_RESPONSE_KEY_ID_MISMATCH"
        }

        val payload = canonicalJson(fields)
        val signer = Signature.getInstance("SHA256withECDSA")
        signer.initSign(privateKey as java.security.PrivateKey)
        signer.update(payload.toByteArray(Charsets.UTF_8))
        return SignedResponse(
            payloadJson = payload,
            signatureBase64 = Base64.getEncoder().encodeToString(signer.sign())
        )
    }

    private fun canonicalJson(fields: Map<String, String>): String =
        fields.toSortedMap().entries.joinToString(
            prefix = "{", postfix = "}", separator = ","
        ) { (key, value) -> "${JSONObject.quote(key)}:${JSONObject.quote(value)}" }

    private fun pemCertificate(certificate: Certificate): String =
        pem("CERTIFICATE", certificate.encoded)

    private fun pem(label: String, der: ByteArray): String {
        val encoded = Base64.getMimeEncoder(64, byteArrayOf(10)).encodeToString(der)
        return "-----BEGIN $label-----\n$encoded\n-----END $label-----\n"
    }

    private fun sha256Hex(bytes: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString("") { byte -> "%02x".format(byte) }
}
