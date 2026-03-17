package com.patrickauld.watches.phone.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * Fetches watch face builds from GitHub Releases.
 *
 * For public repos, no auth is needed. For private repos, set [authToken]
 * to a personal access token with `repo` scope.
 */
class GitHubArtifactSource(
    private val owner: String = "PatrickAuld",
    private val repo: String = "watches",
    private val authToken: String? = null
) {
    private var cachedBuilds: List<AvailableBuild>? = null

    suspend fun fetchAvailableBuilds(forceRefresh: Boolean = false): List<AvailableBuild> {
        if (!forceRefresh) cachedBuilds?.let { return it }

        return withContext(Dispatchers.IO) {
            val releases = fetchReleases()
            val builds = releases.mapNotNull { release -> parseRelease(release) }
            cachedBuilds = builds
            builds
        }
    }

    suspend fun downloadApk(build: AvailableBuild, targetDir: File): File {
        return withContext(Dispatchers.IO) {
            targetDir.mkdirs()
            val targetFile = File(targetDir, "${build.slug}-${build.versionName}.apk")
            val connection = openConnection(build.apkDownloadUrl)
            connection.inputStream.use { input ->
                targetFile.outputStream().use { output ->
                    input.copyTo(output)
                }
            }
            targetFile
        }
    }

    private fun fetchReleases(): List<JSONObject> {
        val url = "https://api.github.com/repos/$owner/$repo/releases"
        val connection = openConnection(url)
        val body = connection.inputStream.bufferedReader().readText()
        val array = JSONArray(body)
        return (0 until array.length()).map { array.getJSONObject(it) }
    }

    private fun parseRelease(release: JSONObject): AvailableBuild? {
        val assets = release.getJSONArray("assets")
        var metadataAsset: JSONObject? = null
        var apkAsset: JSONObject? = null

        for (i in 0 until assets.length()) {
            val asset = assets.getJSONObject(i)
            val name = asset.getString("name")
            when {
                name == "metadata.json" -> metadataAsset = asset
                name.endsWith(".apk") -> apkAsset = asset
            }
        }

        if (metadataAsset == null || apkAsset == null) return null

        val metadataUrl = metadataAsset.getString("browser_download_url")
        val metadata = try {
            val conn = openConnection(metadataUrl)
            JSONObject(conn.inputStream.bufferedReader().readText())
        } catch (e: Exception) {
            return null
        }

        return AvailableBuild(
            slug = metadata.getString("slug"),
            name = metadata.getString("name"),
            commitSha = metadata.getString("commitSha"),
            buildType = metadata.getString("buildType"),
            versionName = metadata.getString("versionName"),
            versionCode = metadata.getInt("versionCode"),
            timestamp = metadata.getString("timestamp"),
            apkDownloadUrl = apkAsset.getString("browser_download_url"),
            releaseTag = release.getString("tag_name")
        )
    }

    private fun openConnection(url: String): HttpURLConnection {
        val connection = URL(url).openConnection() as HttpURLConnection
        connection.setRequestProperty("Accept", "application/vnd.github+json")
        authToken?.let {
            connection.setRequestProperty("Authorization", "Bearer $it")
        }
        return connection
    }
}

data class AvailableBuild(
    val slug: String,
    val name: String,
    val commitSha: String,
    val buildType: String,
    val versionName: String,
    val versionCode: Int,
    val timestamp: String,
    val apkDownloadUrl: String,
    val releaseTag: String
)
