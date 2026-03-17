package com.patrickauld.watches.phone.data

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONObject

/**
 * Manages local state across GitHub builds and watch install state.
 *
 * Merges available builds from [GitHubArtifactSource] with installed
 * face state reported by the watch companion.
 */
class WatchFaceRepository(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("watch_faces", Context.MODE_PRIVATE)

    private val source = GitHubArtifactSource()

    suspend fun getAvailableBuilds(forceRefresh: Boolean = false): List<AvailableBuild> {
        return source.fetchAvailableBuilds(forceRefresh)
    }

    fun getInstalledVersion(slug: String): InstalledState? {
        val json = prefs.getString("installed_$slug", null) ?: return null
        return try {
            val obj = JSONObject(json)
            InstalledState(
                packageName = obj.getString("packageName"),
                versionCode = obj.getInt("versionCode"),
                versionName = obj.getString("versionName")
            )
        } catch (e: Exception) {
            null
        }
    }

    fun updateInstalledState(slug: String, packageName: String, versionCode: Int, versionName: String) {
        val json = JSONObject().apply {
            put("packageName", packageName)
            put("versionCode", versionCode)
            put("versionName", versionName)
        }
        prefs.edit().putString("installed_$slug", json.toString()).apply()
    }

    fun getFaceStatus(build: AvailableBuild): FaceStatus {
        val installed = getInstalledVersion(build.slug) ?: return FaceStatus.NOT_INSTALLED
        return if (build.versionCode > installed.versionCode) {
            FaceStatus.UPDATE_AVAILABLE
        } else {
            FaceStatus.INSTALLED
        }
    }
}

data class InstalledState(
    val packageName: String,
    val versionCode: Int,
    val versionName: String
)

enum class FaceStatus {
    NOT_INSTALLED,
    INSTALLED,
    UPDATE_AVAILABLE
}
