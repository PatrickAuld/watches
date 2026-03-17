package com.patrickauld.watches.phone.sync

import android.content.Context
import com.google.android.gms.wearable.CapabilityClient
import com.google.android.gms.wearable.ChannelClient
import com.google.android.gms.wearable.Wearable
import com.patrickauld.watches.shared.DataLayerPaths
import kotlinx.coroutines.tasks.await
import org.json.JSONObject
import java.io.File

/**
 * Sends watch face APKs to the watch companion via the Wear Data Layer.
 */
class WatchTransfer(private val context: Context) {

    /**
     * Discovers the watch companion node.
     * @return node ID, or null if companion is not reachable
     */
    suspend fun findWatchCompanion(): String? {
        val capabilityInfo = Wearable.getCapabilityClient(context)
            .getCapability(DataLayerPaths.CAPABILITY_WATCH_COMPANION, CapabilityClient.FILTER_REACHABLE)
            .await()
        return capabilityInfo.nodes.firstOrNull()?.id
    }

    /**
     * Transfers an APK file to the watch companion.
     */
    suspend fun transferApk(nodeId: String, apkFile: File): Result<Unit> = runCatching {
        val channelClient = Wearable.getChannelClient(context)
        val channel = channelClient.openChannel(nodeId, DataLayerPaths.CHANNEL_WATCHFACE_APK).await()

        try {
            val outputStream = channelClient.getOutputStream(channel).await()
            outputStream.use { output ->
                apkFile.inputStream().use { input ->
                    input.copyTo(output)
                }
            }
        } finally {
            channelClient.close(channel).await()
        }
    }

    /**
     * Sends an install request to the watch companion.
     */
    suspend fun requestInstall(
        nodeId: String,
        slug: String,
        packageName: String,
        isUpdate: Boolean
    ): Result<Unit> = runCatching {
        val json = JSONObject().apply {
            put("slug", slug)
            put("packageName", packageName)
            put("isUpdate", isUpdate)
        }
        Wearable.getMessageClient(context)
            .sendMessage(nodeId, DataLayerPaths.MESSAGE_REQUEST_INSTALL, json.toString().toByteArray())
            .await()
    }

    /**
     * Sends an activation request to the watch companion.
     */
    suspend fun requestActivate(nodeId: String, packageName: String): Result<Unit> = runCatching {
        val json = JSONObject().apply {
            put("packageName", packageName)
        }
        Wearable.getMessageClient(context)
            .sendMessage(nodeId, DataLayerPaths.MESSAGE_REQUEST_ACTIVATE, json.toString().toByteArray())
            .await()
    }
}
