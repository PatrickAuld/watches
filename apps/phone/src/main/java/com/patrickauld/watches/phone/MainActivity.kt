package com.patrickauld.watches.phone

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.patrickauld.watches.phone.data.AvailableBuild
import com.patrickauld.watches.phone.data.FaceStatus
import com.patrickauld.watches.phone.data.GitHubArtifactSource
import com.patrickauld.watches.phone.data.WatchFaceRepository
import com.patrickauld.watches.phone.sync.WatchTransfer
import com.patrickauld.watches.phone.ui.BuildListScreen
import com.patrickauld.watches.phone.ui.FaceListScreen
import com.patrickauld.watches.phone.ui.FaceSummary
import com.patrickauld.watches.phone.ui.InstallPhase
import com.patrickauld.watches.phone.ui.InstallScreen
import kotlinx.coroutines.launch
import java.io.File

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                MainApp(applicationContext)
            }
        }
    }
}

sealed class Screen {
    data object FaceList : Screen()
    data class BuildList(val slug: String) : Screen()
    data class Install(val build: AvailableBuild) : Screen()
}

class MainViewModel : ViewModel() {
    var screen by mutableStateOf<Screen>(Screen.FaceList)
        private set
    var faces by mutableStateOf<List<FaceSummary>>(emptyList())
        private set
    var builds by mutableStateOf<List<AvailableBuild>>(emptyList())
        private set
    var installPhase by mutableStateOf(InstallPhase.DOWNLOADING)
        private set
    var errorMessage by mutableStateOf<String?>(null)
        private set
    var isLoading by mutableStateOf(false)
        private set

    private var allBuilds: List<AvailableBuild> = emptyList()

    fun loadFaces(repo: WatchFaceRepository) {
        viewModelScope.launch {
            isLoading = true
            try {
                allBuilds = repo.getAvailableBuilds(forceRefresh = true)
                faces = allBuilds
                    .groupBy { it.slug }
                    .map { (slug, slugBuilds) ->
                        val latest = slugBuilds.maxByOrNull { it.versionCode } ?: slugBuilds.first()
                        FaceSummary(
                            slug = slug,
                            name = latest.name,
                            latestVersion = latest.versionName,
                            status = repo.getFaceStatus(latest)
                        )
                    }
            } catch (e: Exception) {
                errorMessage = e.message
            } finally {
                isLoading = false
            }
        }
    }

    fun navigateToBuilds(slug: String) {
        builds = allBuilds.filter { it.slug == slug }.sortedByDescending { it.versionCode }
        screen = Screen.BuildList(slug)
    }

    fun navigateToInstall(build: AvailableBuild) {
        installPhase = InstallPhase.DOWNLOADING
        errorMessage = null
        screen = Screen.Install(build)
    }

    fun startInstall(build: AvailableBuild, repo: WatchFaceRepository, transfer: WatchTransfer, cacheDir: File) {
        viewModelScope.launch {
            try {
                // Download
                installPhase = InstallPhase.DOWNLOADING
                val source = GitHubArtifactSource()
                val apkFile = source.downloadApk(build, cacheDir)

                // Find watch
                val nodeId = transfer.findWatchCompanion()
                if (nodeId == null) {
                    installPhase = InstallPhase.ERROR
                    errorMessage = "Watch companion not found. Is it installed and connected?"
                    return@launch
                }

                // Transfer
                installPhase = InstallPhase.TRANSFERRING
                transfer.transferApk(nodeId, apkFile).getOrThrow()

                // Request install
                installPhase = InstallPhase.INSTALLING
                val isUpdate = repo.getInstalledVersion(build.slug) != null
                val packageName = "com.patrickauld.watches.companion.watchfacepush.${build.slug}"
                transfer.requestInstall(nodeId, build.slug, packageName, isUpdate).getOrThrow()

                // Update local state
                repo.updateInstalledState(build.slug, packageName, build.versionCode, build.versionName)
                installPhase = InstallPhase.SUCCESS
            } catch (e: Exception) {
                installPhase = InstallPhase.ERROR
                errorMessage = e.message
            }
        }
    }

    fun requestActivate(build: AvailableBuild, transfer: WatchTransfer) {
        viewModelScope.launch {
            try {
                val nodeId = transfer.findWatchCompanion()
                if (nodeId == null) {
                    errorMessage = "Watch companion not found"
                    return@launch
                }
                val packageName = "com.patrickauld.watches.companion.watchfacepush.${build.slug}"
                transfer.requestActivate(nodeId, packageName).getOrThrow()
            } catch (e: Exception) {
                errorMessage = e.message
            }
        }
    }

    fun navigateBack() {
        screen = Screen.FaceList
    }
}

@Composable
fun MainApp(context: android.content.Context, viewModel: MainViewModel = viewModel()) {
    val repo = WatchFaceRepository(context)
    val transfer = WatchTransfer(context)

    LaunchedEffect(Unit) {
        viewModel.loadFaces(repo)
    }

    when (val currentScreen = viewModel.screen) {
        is Screen.FaceList -> {
            if (viewModel.isLoading) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else {
                FaceListScreen(
                    faces = viewModel.faces,
                    onFaceClick = { slug -> viewModel.navigateToBuilds(slug) }
                )
            }
        }
        is Screen.BuildList -> {
            val installed = repo.getInstalledVersion(currentScreen.slug)
            BuildListScreen(
                faceName = viewModel.builds.firstOrNull()?.name ?: currentScreen.slug,
                builds = viewModel.builds,
                installedVersionCode = installed?.versionCode,
                onInstallClick = { build ->
                    viewModel.navigateToInstall(build)
                    viewModel.startInstall(build, repo, transfer, File(context.cacheDir, "apks"))
                },
                onBack = { viewModel.navigateBack() }
            )
        }
        is Screen.Install -> {
            InstallScreen(
                faceName = currentScreen.build.name,
                phase = viewModel.installPhase,
                errorMessage = viewModel.errorMessage,
                onSetActive = {
                    viewModel.requestActivate(currentScreen.build, transfer)
                },
                onDone = {
                    viewModel.loadFaces(repo)
                    viewModel.navigateBack()
                }
            )
        }
    }
}
