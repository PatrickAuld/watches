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
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.patrickauld.watches.phone.data.AvailableBuild
import com.patrickauld.watches.phone.data.FaceStatus
import com.patrickauld.watches.phone.data.InstalledState
import com.patrickauld.watches.phone.data.WatchFaceRepository
import com.patrickauld.watches.phone.sync.WatchTransfer
import com.patrickauld.watches.phone.sync.AutoUpdates
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
    var installed by mutableStateOf<Map<String, InstalledState>>(emptyMap())
        private set
    var isActive by mutableStateOf(false)
        private set

    private var allBuilds: List<AvailableBuild> = emptyList()

    fun loadFaces(repo: WatchFaceRepository, transfer: WatchTransfer) {
        viewModelScope.launch {
            isLoading = true
            try {
                allBuilds = repo.getAvailableBuilds()
                runCatching { refreshInstalled(transfer) }
                faces = allBuilds
                    .groupBy { it.slug }
                    .map { (slug, slugBuilds) ->
                        val latest = slugBuilds.maxByOrNull { it.versionCode } ?: slugBuilds.first()
                        FaceSummary(
                            slug = slug,
                            name = latest.name,
                            latestVersion = latest.versionName,
                            status = when (val current = installed[latest.packageName]) {
                                null -> FaceStatus.NOT_INSTALLED
                                else -> if (current.versionCode < latest.versionCode) FaceStatus.UPDATE_AVAILABLE else FaceStatus.INSTALLED
                            }
                        )
                    }
            } catch (e: Exception) {
                errorMessage = e.message
            } finally {
                isLoading = false
            }
        }
    }

    private suspend fun refreshInstalled(transfer: WatchTransfer) {
        val node = transfer.findWatchCompanion() ?: run {
            installed = emptyMap()
            return
        }
        val reply = transfer.installed(node)
        val faces = reply.getJSONArray("faces")
        installed = (0 until faces.length()).associate { index ->
            val face = faces.getJSONObject(index)
            val packageName = face.getString("packageName")
            packageName to InstalledState(packageName, face.getInt("versionCode"), face.getBoolean("isActive"))
        }
    }

    fun navigateToBuilds(slug: String) {
        builds = allBuilds.filter { it.slug == slug }.sortedByDescending { it.versionCode }
        screen = Screen.BuildList(slug)
    }

    fun navigateToInstall(build: AvailableBuild) {
        installPhase = InstallPhase.DOWNLOADING
        isActive = false
        errorMessage = null
        screen = Screen.Install(build)
    }

    fun startInstall(build: AvailableBuild, repo: WatchFaceRepository, transfer: WatchTransfer, cacheDir: File) {
        viewModelScope.launch {
            try {
                // Download
                installPhase = InstallPhase.DOWNLOADING
                val apkFile = repo.downloadApk(build, cacheDir)

                // Find watch
                val nodeId = transfer.findWatchCompanion()
                if (nodeId == null) {
                    installPhase = InstallPhase.ERROR
                    errorMessage = "Watch companion not found. Is it installed and connected?"
                    return@launch
                }

                // Transfer
                installPhase = InstallPhase.TRANSFERRING
                val result = transfer.install(nodeId, apkFile, build.packageName, build.sha256, build.validationToken) {
                    installPhase = InstallPhase.INSTALLING
                }
                require(result.getInt("versionCode") == build.versionCode) { "Watch installed a different version" }
                isActive = result.getBoolean("isActive")
                installed = installed + (build.packageName to InstalledState(build.packageName, build.versionCode, isActive))
                installPhase = InstallPhase.SUCCESS
                runCatching { refreshInstalled(transfer) }
            } catch (e: Exception) {
                installPhase = InstallPhase.ERROR
                errorMessage = e.message
            }
        }
    }

    fun requestActivate(build: AvailableBuild, transfer: WatchTransfer) {
        viewModelScope.launch {
            try {
                errorMessage = null
                val nodeId = transfer.findWatchCompanion()
                if (nodeId == null) {
                    errorMessage = "Watch companion not found"
                    return@launch
                }
                transfer.activate(nodeId, build.packageName)
                isActive = true
                refreshInstalled(transfer)
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
    val repo = remember { WatchFaceRepository() }
    val transfer = remember { WatchTransfer(context) }
    var autoUpdates by remember { mutableStateOf(AutoUpdates.enabled(context)) }

    LaunchedEffect(Unit) {
        viewModel.loadFaces(repo, transfer)
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
                    autoUpdates = autoUpdates,
                    onAutoUpdatesChange = { enabled ->
                        AutoUpdates.setEnabled(context, enabled)
                        autoUpdates = enabled
                    },
                    onFaceClick = { slug -> viewModel.navigateToBuilds(slug) }
                )
            }
        }
        is Screen.BuildList -> {
            val installed = viewModel.builds.firstOrNull()?.let { viewModel.installed[it.packageName] }
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
                isActive = viewModel.isActive,
                onSetActive = {
                    viewModel.requestActivate(currentScreen.build, transfer)
                },
                onDone = {
                    viewModel.loadFaces(repo, transfer)
                    viewModel.navigateBack()
                }
            )
        }
    }
}
