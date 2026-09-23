package com.patrickauld.watches.companion

import android.content.Context
import android.content.pm.PackageManager
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

    suspend fun installOrUpdate(apkPath: String, validationToken: String): Result<InstallOutcome> = runCatching {
        val manager = getManager()
        val installed = manager.listWatchFaces().installedWatchFaceDetails
        val existing = installed.firstOrNull()
        val wasActive = existing?.let { manager.isWatchFaceActive(it.packageName) } ?: false
        val slot = openParcelFileDescriptor(apkPath).use { apkFd ->
            if (existing == null) {
                manager.addWatchFace(apkFd, validationToken)
            } else {
                manager.updateWatchFace(existing.slotId, apkFd, validationToken)
            }
        }
        InstallOutcome(slot.packageName, slot.versionCode, wasActive)
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
        if (!manager.isWatchFaceActive(packageName)) {
            require(context.checkSelfPermission("com.google.wear.permission.SET_PUSHED_WATCH_FACE_AS_ACTIVE") ==
                PackageManager.PERMISSION_GRANTED) { "Open the companion app on the watch and allow face activation" }
            val prefs = context.getSharedPreferences("activation", Context.MODE_PRIVATE)
            require(!prefs.getBoolean("used", false)) {
                "Choose this face manually in the watch face picker; automatic activation can only be used once"
            }
            manager.setWatchFaceAsActive(existing.slotId)
            prefs.edit().putBoolean("used", true).apply()
        }
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

data class InstallOutcome(
    val packageName: String,
    val versionCode: Long,
    val wasActive: Boolean
)
