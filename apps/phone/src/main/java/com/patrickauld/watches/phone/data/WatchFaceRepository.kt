package com.patrickauld.watches.phone.data

class WatchFaceRepository {
    private val source = GitHubArtifactSource()

    suspend fun getAvailableBuilds(): List<AvailableBuild> = source.fetchAvailableBuilds()

    suspend fun downloadApk(build: AvailableBuild, directory: java.io.File): java.io.File =
        source.downloadApk(build, directory)
}

data class InstalledState(
    val packageName: String,
    val versionCode: Int,
    val isActive: Boolean
)

enum class FaceStatus {
    NOT_INSTALLED,
    INSTALLED,
    UPDATE_AVAILABLE
}
