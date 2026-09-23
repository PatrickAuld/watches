package com.patrickauld.watches.phone.sync

import android.content.Context
import com.google.android.gms.wearable.CapabilityClient
import com.google.android.gms.wearable.MessageClient
import com.google.android.gms.wearable.Wearable
import com.patrickauld.watches.shared.DataLayerPaths
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withTimeout
import org.json.JSONObject
import java.io.File
import java.util.UUID

class WatchTransfer(private val context: Context) {
    suspend fun findWatchCompanion(): String? =
        Wearable.getCapabilityClient(context)
            .getCapability(DataLayerPaths.CAPABILITY_WATCH_COMPANION, CapabilityClient.FILTER_REACHABLE)
            .await().nodes.firstOrNull()?.id

    suspend fun install(
        nodeId: String,
        apkFile: File,
        packageName: String,
        sha256: String,
        validationToken: String,
        onTransferred: () -> Unit
    ): JSONObject {
        val id = UUID.randomUUID().toString()
        return exchange(nodeId, DataLayerPaths.MESSAGE_REQUEST_INSTALL, id, JSONObject().apply {
            put("packageName", packageName)
            put("sha256", sha256)
            put("validationToken", validationToken)
        }) {
            val client = Wearable.getChannelClient(context)
            val channel = client.openChannel(nodeId, DataLayerPaths.CHANNEL_WATCHFACE_APK + id).await()
            try {
                client.getOutputStream(channel).await().use { output ->
                    apkFile.inputStream().use { input -> input.copyTo(output) }
                }
            } finally {
                client.close(channel).await()
            }
            onTransferred()
        }
    }

    suspend fun activate(nodeId: String, packageName: String): JSONObject {
        val id = UUID.randomUUID().toString()
        return exchange(nodeId, DataLayerPaths.MESSAGE_REQUEST_ACTIVATE, id,
            JSONObject().put("packageName", packageName))
    }

    suspend fun installed(nodeId: String): JSONObject {
        val id = UUID.randomUUID().toString()
        return exchange(nodeId, DataLayerPaths.MESSAGE_REQUEST_STATE, id, JSONObject())
    }

    private suspend fun exchange(
        nodeId: String,
        path: String,
        id: String,
        data: JSONObject,
        beforeSend: suspend () -> Unit = {}
    ): JSONObject {
        val client = Wearable.getMessageClient(context)
        val response = CompletableDeferred<JSONObject>()
        val listener = MessageClient.OnMessageReceivedListener { event ->
            if (event.path == DataLayerPaths.MESSAGE_INSTALL_STATUS && event.sourceNodeId == nodeId) {
                val reply = runCatching { JSONObject(String(event.data)) }.getOrNull()
                if (reply?.optString("id") == id) response.complete(reply)
            }
        }
        client.addListener(listener).await()
        try {
            beforeSend()
            client.sendMessage(nodeId, path, data.put("id", id).toString().toByteArray()).await()
            val reply = withTimeout(150_000) { response.await() }
            if (reply.getString("status") != "success") {
                error(reply.optString("message", "Watch request failed"))
            }
            return reply
        } finally {
            client.removeListener(listener).await()
        }
    }
}
