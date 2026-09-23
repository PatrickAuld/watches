package com.patrickauld.watches.phone.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

class GitHubArtifactSource(
    private val owner: String = "PatrickAuld",
    private val repo: String = "watches"
) {
    suspend fun fetchAvailableBuilds(): List<AvailableBuild> = withContext(Dispatchers.IO) {
        val body = openConnection("https://api.github.com/repos/$owner/$repo/releases?per_page=30")
            .inputStream.bufferedReader().use { it.readText() }
        val releases = JSONArray(body)
        val builds = mutableListOf<AvailableBuild>()
        for (i in 0 until releases.length()) {
            val release = releases.getJSONObject(i)
            val assets = release.getJSONArray("assets")
            val urls = (0 until assets.length()).associate { index ->
                val asset = assets.getJSONObject(index)
                asset.getString("name") to asset.getString("browser_download_url")
            }
            val catalogUrl = urls["catalog.json"] ?: continue
            val catalog = JSONObject(openConnection(catalogUrl).inputStream.bufferedReader().use { it.readText() })
            val entries = catalog.getJSONArray("faces")
            for (j in 0 until entries.length()) {
                val face = entries.getJSONObject(j)
                val filename = face.getString("apk")
                val apkUrl = urls[filename] ?: continue
                builds += AvailableBuild(
                    slug = face.getString("slug"),
                    name = face.getString("name"),
                    commitSha = catalog.getString("commitSha"),
                    versionName = face.getString("versionName"),
                    versionCode = face.getInt("versionCode"),
                    timestamp = catalog.getString("timestamp"),
                    apkDownloadUrl = apkUrl,
                    packageName = face.getString("packageName"),
                    sha256 = face.getString("sha256"),
                    validationToken = face.getString("validationToken"),
                    releaseTag = release.getString("tag_name")
                )
            }
        }
        builds
    }

    suspend fun downloadApk(build: AvailableBuild, targetDir: File): File = withContext(Dispatchers.IO) {
        targetDir.mkdirs()
        val targetFile = File(targetDir, "${build.slug}-${build.versionCode}.apk")
        try {
            openConnection(build.apkDownloadUrl).inputStream.use { input ->
                targetFile.outputStream().use { output -> input.copyTo(output) }
            }
            val checksum = MessageDigest.getInstance("SHA-256")
                .digest(targetFile.readBytes()).joinToString("") { "%02x".format(it) }
            require(checksum.equals(build.sha256, ignoreCase = true)) { "Downloaded APK checksum mismatch" }
            targetFile
        } catch (error: Exception) {
            targetFile.delete()
            throw error
        }
    }

    private fun openConnection(url: String): HttpURLConnection =
        (URL(url).openConnection() as HttpURLConnection).apply {
            connectTimeout = 15_000
            readTimeout = 30_000
            setRequestProperty("Accept", "application/vnd.github+json")
        }
}

data class AvailableBuild(
    val slug: String,
    val name: String,
    val commitSha: String,
    val versionName: String,
    val versionCode: Int,
    val timestamp: String,
    val apkDownloadUrl: String,
    val packageName: String,
    val sha256: String,
    val validationToken: String,
    val releaseTag: String
)
