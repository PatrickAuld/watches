package com.patrickauld.watches.companion

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.wear.compose.material3.MaterialTheme
import androidx.wear.compose.material3.Text
import kotlinx.coroutines.launch

class CompanionActivity : ComponentActivity() {

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { /* permissions granted or denied */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestPushPermissions()
        setContent {
            MaterialTheme {
                CompanionScreen()
            }
        }
    }

    private fun requestPushPermissions() {
        val permissions = arrayOf(
            "com.google.wear.permission.PUSH_WATCH_FACES",
            "com.google.wear.permission.SET_PUSHED_WATCH_FACE_AS_ACTIVE"
        )
        val needed = permissions.filter {
            checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED
        }
        if (needed.isNotEmpty()) {
            permissionLauncher.launch(needed.toTypedArray())
        }
    }
}

class CompanionViewModel : ViewModel() {
    var installedFaces by mutableStateOf<List<InstalledFace>>(emptyList())
        private set
    var statusMessage by mutableStateOf("Ready")
        private set

    private val installer by lazy { WatchFaceInstaller(android.app.Application()) }

    fun loadInstalledFaces(context: android.content.Context) {
        val inst = WatchFaceInstaller(context)
        viewModelScope.launch {
            inst.listInstalled().fold(
                onSuccess = { faces -> installedFaces = faces },
                onFailure = { e -> statusMessage = "Error: ${e.message}" }
            )
        }
    }
}

@Composable
fun CompanionScreen(viewModel: CompanionViewModel = viewModel()) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "Watch Face Push",
            style = MaterialTheme.typography.titleMedium,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth()
        )

        Text(
            text = viewModel.statusMessage,
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 8.dp)
        )

        if (viewModel.installedFaces.isNotEmpty()) {
            Text(
                text = "${viewModel.installedFaces.size} face(s) installed",
                style = MaterialTheme.typography.bodySmall,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 4.dp)
            )
        }
    }
}
