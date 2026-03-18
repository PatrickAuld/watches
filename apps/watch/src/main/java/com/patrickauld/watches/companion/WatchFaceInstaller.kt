package com.patrickauld.watches.companion

import android.content.Context
import android.os.ParcelFileDescriptor
import androidx.wear.watchfacepush.WatchFacePushManager
import androidx.wear.watchfacepush.WatchFacePushManagerFactory

/**
 * Wrapper around [WatchFacePushManager] that isolates the API surface.
 */
class WatchFaceInstaller(private val context: Context) {

    private fun getManager(): WatchFacePushManager {
        return WatchFacePushManagerFactory.createWatchFacePushManager(context)
    }

    suspend fun install(apkPath: String, validationToken: String?): Result<Unit> = runCatching {
        val token = validationToken ?: error("validationToken is required for watch face install")
        val manager = getManager()
        openParcelFileDescriptor(apkPath).use { apkFd ->
            manager.addWatchFace(apkFd, token)
        }
    }

    suspend fun update(packageName: String, apkPath: String, validationToken: String?): Result<Unit> = runCatching {
        val token = validationToken ?: error("validationToken is required for watch face update")
        val manager = getManager()
        val existing = manager.listWatchFaces().installedWatchFaceDetails
            .firstOrNull { it.packageName == packageName }
            ?: error("No installed watch face found for package $packageName")

        openParcelFileDescriptor(apkPath).use { apkFd ->
            manager.updateWatchFace(existing.slotId, apkFd, token)
        }
    }

    suspend fun remove(packageName: String): Result<Unit> = runCatching {
        val manager = getManager()
        val existing = manager.listWatchFaces().installedWatchFaceDetails
            .firstOrNull { it.packageName == packageName }
            ?: error("No installed watch face found for package $packageName")
        manager.removeWatchFace(existing.slotId)
    }

    suspend fun setActive(packageName: String): Result<Unit> = runCatching {
        val manager = getManager()
        val existing = manager.listWatchFaces().installedWatchFaceDetails
            .firstOrNull { it.packageName == packageName }
            ?: error("No installed watch face found for package $packageName")
        manager.setWatchFaceAsActive(existing.slotId)
    }

    suspend fun listInstalled(): Result<List<InstalledFace>> = runCatching {
        val manager = getManager()
        manager.listWatchFaces().installedWatchFaceDetails.map { info ->
            InstalledFace(
                packageName = info.packageName,
                versionCode = info.versionCode,
                isActive = manager.isWatchFaceActive(info.packageName)
            )
        }
    }

    private fun openParcelFileDescriptor(apkPath: String): ParcelFileDescriptor {
        return ParcelFileDescriptor.open(
            java.io.File(apkPath),
            ParcelFileDescriptor.MODE_READ_ONLY
        )
    }
}

data class InstalledFace(
    val packageName: String,
    val versionCode: Long,
    val isActive: Boolean
)
