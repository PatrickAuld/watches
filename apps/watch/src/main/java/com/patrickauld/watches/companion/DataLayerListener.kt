package com.patrickauld.watches.companion

import com.google.android.gms.wearable.ChannelClient
import android.os.BatteryManager
import com.google.android.gms.wearable.MessageEvent
import com.google.android.gms.wearable.Wearable
import com.google.android.gms.wearable.WearableListenerService
import com.patrickauld.watches.shared.DataLayerPaths
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withTimeout
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.ConcurrentHashMap

class DataLayerListener : WearableListenerService() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val installer by lazy { WatchFaceInstaller(applicationContext) }
    private val transfers = ConcurrentHashMap<String, CompletableDeferred<File>>()

    private fun transfer(id: String): CompletableDeferred<File> =
        transfers.computeIfAbsent(id) { CompletableDeferred() }

    override fun onChannelOpened(channel: ChannelClient.Channel) {
        if (!channel.path.startsWith(DataLayerPaths.CHANNEL_WATCHFACE_APK)) return
        val id = channel.path.removePrefix(DataLayerPaths.CHANNEL_WATCHFACE_APK)
        if (!Regex("[0-9a-f-]{36}").matches(id)) return
        scope.launch {
            try {
                val directory = File(filesDir, "watchfaces").apply { mkdirs() }
                val file = File(directory, "$id.apk")
                Wearable.getChannelClient(applicationContext).getInputStream(channel).await().use { input ->
                    file.outputStream().use { output -> input.copyTo(output) }
                }
                transfer(id).complete(file)
            } catch (error: Exception) {
                transfer(id).completeExceptionally(error)
            }
        }
    }

    override fun onMessageReceived(event: MessageEvent) {
        when (event.path) {
            DataLayerPaths.MESSAGE_REQUEST_INSTALL -> scope.launch { install(event) }
            DataLayerPaths.MESSAGE_REQUEST_ACTIVATE -> scope.launch { activate(event) }
            DataLayerPaths.MESSAGE_REQUEST_STATE -> scope.launch { state(event) }
        }
    }

    private suspend fun install(event: MessageEvent) {
        val request = JSONObject(String(event.data))
        val id = request.getString("id")
        var file: File? = null
        try {
            val apkFile = withTimeout(120_000) { transfer(id).await() }
            file = apkFile
            val digest = MessageDigest.getInstance("SHA-256").digest(apkFile.readBytes())
                .joinToString("") { "%02x".format(it) }
            require(digest.equals(request.getString("sha256"), ignoreCase = true)) { "APK checksum mismatch" }
            val outcome = installer.installOrUpdate(apkFile.absolutePath, request.getString("validationToken")).getOrThrow()
            require(outcome.packageName == request.getString("packageName")) { "Installed package mismatch" }
            respond(event.sourceNodeId, id, "install", "success", JSONObject().apply {
                put("packageName", outcome.packageName)
                put("versionCode", outcome.versionCode)
                put("isActive", outcome.wasActive)
            })
        } catch (error: Exception) {
            respond(event.sourceNodeId, id, "install", "error", JSONObject().put("message", error.message ?: "Install failed"))
        } finally {
            transfers.remove(id)
            file?.delete()
        }
    }

    private suspend fun activate(event: MessageEvent) {
        val request = JSONObject(String(event.data))
        val id = request.getString("id")
        try {
            val packageName = request.getString("packageName")
            installer.setActive(packageName).getOrThrow()
            respond(event.sourceNodeId, id, "activate", "success", JSONObject().put("packageName", packageName))
        } catch (error: Exception) {
            respond(event.sourceNodeId, id, "activate", "error", JSONObject().put("message", error.message ?: "Activation failed"))
        }
    }

    private suspend fun state(event: MessageEvent) {
        val request = JSONObject(String(event.data))
        val id = request.getString("id")
        try {
            val faces = JSONArray()
            installer.listInstalled().getOrThrow().forEach { face ->
                faces.put(JSONObject().apply {
                    put("packageName", face.packageName)
                    put("versionCode", face.versionCode)
                    put("isActive", face.isActive)
                })
            }
            val charging = (getSystemService(BATTERY_SERVICE) as BatteryManager).isCharging
            respond(event.sourceNodeId, id, "state", "success", JSONObject().put("faces", faces).put("charging", charging))
        } catch (error: Exception) {
            respond(event.sourceNodeId, id, "state", "error", JSONObject().put("message", error.message ?: "State unavailable"))
        }
    }

    private suspend fun respond(nodeId: String, id: String, action: String, status: String, data: JSONObject) {
        val response = data.put("id", id).put("action", action).put("status", status)
        Wearable.getMessageClient(applicationContext)
            .sendMessage(nodeId, DataLayerPaths.MESSAGE_INSTALL_STATUS, response.toString().toByteArray()).await()
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
