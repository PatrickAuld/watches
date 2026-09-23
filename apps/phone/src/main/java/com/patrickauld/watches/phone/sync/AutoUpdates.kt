package com.patrickauld.watches.phone.sync

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkerParameters
import androidx.work.WorkManager
import com.patrickauld.watches.phone.data.WatchFaceRepository
import java.io.File
import java.util.concurrent.TimeUnit

object AutoUpdates {
    private const val WORK_NAME = "watch-face-auto-updates"
    private const val PREFS = "watch_face_settings"

    fun enabled(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean("auto_updates", false)

    fun setEnabled(context: Context, enabled: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean("auto_updates", enabled).apply()
        val manager = WorkManager.getInstance(context)
        if (enabled) {
            val request = PeriodicWorkRequestBuilder<AutoUpdateWorker>(12, TimeUnit.HOURS)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
            manager.enqueueUniquePeriodicWork(WORK_NAME, ExistingPeriodicWorkPolicy.UPDATE, request)
        } else {
            manager.cancelUniqueWork(WORK_NAME)
        }
    }
}

class AutoUpdateWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        if (!AutoUpdates.enabled(applicationContext)) return Result.success()
        return try {
            val transfer = WatchTransfer(applicationContext)
            val node = transfer.findWatchCompanion() ?: return Result.success()
            val state = transfer.installed(node)
            if (!state.optBoolean("charging")) return Result.success()
            val installed = state.getJSONArray("faces")
            val builds = WatchFaceRepository().getAvailableBuilds()
            for (index in 0 until installed.length()) {
                val face = installed.getJSONObject(index)
                val packageName = face.getString("packageName")
                val latest = builds.filter { it.packageName == packageName }.maxByOrNull { it.versionCode }
                    ?: continue
                if (latest.versionCode <= face.getInt("versionCode")) continue
                val apk = WatchFaceRepository().downloadApk(latest, File(applicationContext.cacheDir, "apks"))
                val result = transfer.install(node, apk, latest.packageName, latest.sha256, latest.validationToken) {}
                require(result.getInt("versionCode") == latest.versionCode) { "Watch installed an unexpected version" }
            }
            Result.success()
        } catch (error: Exception) {
            Result.retry()
        }
    }
}
