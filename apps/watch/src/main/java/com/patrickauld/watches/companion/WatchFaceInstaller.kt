package com.patrickauld.watches.companion

import android.content.Context
import androidx.wear.watchface.push.WatchFacePushManager

/**
 * Wrapper around [WatchFacePushManager] that isolates the alpha API surface.
 *
 * All Watch Face Push API calls go through this class so that API changes
 * only require updating one file.
 */
class WatchFaceInstaller(private val context: Context) {

    private suspend fun getManager(): WatchFacePushManager {
        return WatchFacePushManager.createAsync(context)
    }

    suspend fun install(apkPath: String, validationToken: String?): Result<Unit> = runCatching {
        val manager = getManager()
        val apkFile = java.io.File(apkPath)
        manager.addWatchFace(apkFile, validationToken)
    }

    suspend fun update(packageName: String, apkPath: String): Result<Unit> = runCatching {
        val manager = getManager()
        val apkFile = java.io.File(apkPath)
        manager.updateWatchFace(packageName, apkFile)
    }

    suspend fun remove(packageName: String): Result<Unit> = runCatching {
        val manager = getManager()
        manager.removeWatchFace(packageName)
    }

    suspend fun setActive(packageName: String): Result<Unit> = runCatching {
        val manager = getManager()
        manager.setWatchFaceAsActive(packageName)
    }

    suspend fun listInstalled(): Result<List<InstalledFace>> = runCatching {
        val manager = getManager()
        manager.listWatchFaces().map { info ->
            InstalledFace(
                packageName = info.packageName,
                versionCode = info.versionCode,
                isActive = info.isActive
            )
        }
    }
}

data class InstalledFace(
    val packageName: String,
    val versionCode: Long,
    val isActive: Boolean
)
