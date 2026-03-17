package com.patrickauld.watches.companion

import com.google.android.gms.wearable.ChannelClient
import com.google.android.gms.wearable.MessageEvent
import com.google.android.gms.wearable.Wearable
import com.google.android.gms.wearable.WearableListenerService
import com.patrickauld.watches.shared.DataLayerPaths
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import org.json.JSONObject
import java.io.File

/**
 * Background service that receives watch face APKs from the phone app
 * via the Wear Data Layer and installs them using [WatchFaceInstaller].
 */
class DataLayerListener : WearableListenerService() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val installer by lazy { WatchFaceInstaller(applicationContext) }

    override fun onChannelOpened(channel: ChannelClient.Channel) {
        if (channel.path != DataLayerPaths.CHANNEL_WATCHFACE_APK) return

        scope.launch {
            try {
                val inputStream = Wearable.getChannelClient(applicationContext)
                    .getInputStream(channel).await()

                val watchfacesDir = File(filesDir, "watchfaces").apply { mkdirs() }
                val tempFile = File(watchfacesDir, "incoming.apk")

                inputStream.use { input ->
                    tempFile.outputStream().use { output ->
                        input.copyTo(output)
                    }
                }
            } catch (e: Exception) {
                sendStatus(channel.nodeId, "error", e.message ?: "Failed to receive APK")
            }
        }
    }

    override fun onMessageReceived(messageEvent: MessageEvent) {
        when (messageEvent.path) {
            DataLayerPaths.MESSAGE_REQUEST_INSTALL -> handleInstallRequest(messageEvent)
            DataLayerPaths.MESSAGE_REQUEST_ACTIVATE -> handleActivateRequest(messageEvent)
        }
    }

    private fun handleInstallRequest(messageEvent: MessageEvent) {
        scope.launch {
            try {
                val json = JSONObject(String(messageEvent.data))
                val slug = json.getString("slug")
                val packageName = json.getString("packageName")
                val isUpdate = json.optBoolean("isUpdate", false)

                val watchfacesDir = File(filesDir, "watchfaces")
                val apkFile = File(watchfacesDir, "incoming.apk")
                val targetFile = File(watchfacesDir, "$slug.apk")

                if (apkFile.exists()) {
                    apkFile.renameTo(targetFile)
                }

                val result = if (isUpdate) {
                    installer.update(packageName, targetFile.absolutePath)
                } else {
                    installer.install(targetFile.absolutePath, null)
                }

                result.fold(
                    onSuccess = {
                        sendStatus(messageEvent.sourceNodeId, "success", "$slug installed")
                    },
                    onFailure = { e ->
                        sendStatus(messageEvent.sourceNodeId, "error", e.message ?: "Install failed")
                    }
                )
            } catch (e: Exception) {
                sendStatus(messageEvent.sourceNodeId, "error", e.message ?: "Request failed")
            }
        }
    }

    private fun handleActivateRequest(messageEvent: MessageEvent) {
        scope.launch {
            try {
                val json = JSONObject(String(messageEvent.data))
                val packageName = json.getString("packageName")

                installer.setActive(packageName).fold(
                    onSuccess = {
                        sendStatus(messageEvent.sourceNodeId, "success", "Face activated")
                    },
                    onFailure = { e ->
                        sendStatus(messageEvent.sourceNodeId, "error", e.message ?: "Activation failed")
                    }
                )
            } catch (e: Exception) {
                sendStatus(messageEvent.sourceNodeId, "error", e.message ?: "Activate request failed")
            }
        }
    }

    private suspend fun sendStatus(nodeId: String, status: String, message: String) {
        val json = JSONObject().apply {
            put("status", status)
            put("message", message)
        }
        Wearable.getMessageClient(applicationContext)
            .sendMessage(nodeId, DataLayerPaths.MESSAGE_INSTALL_STATUS, json.toString().toByteArray())
            .await()
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
    }
}
