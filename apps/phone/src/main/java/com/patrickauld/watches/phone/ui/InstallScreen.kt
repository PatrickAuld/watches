package com.patrickauld.watches.phone.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

enum class InstallPhase {
    DOWNLOADING,
    TRANSFERRING,
    INSTALLING,
    SUCCESS,
    ERROR
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InstallScreen(
    faceName: String,
    phase: InstallPhase,
    errorMessage: String? = null,
    onSetActive: () -> Unit = {},
    onDone: () -> Unit = {}
) {
    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Installing $faceName") })
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            when (phase) {
                InstallPhase.DOWNLOADING -> {
                    CircularProgressIndicator()
                    Spacer(modifier = Modifier.height(16.dp))
                    Text("Downloading APK...")
                }
                InstallPhase.TRANSFERRING -> {
                    CircularProgressIndicator()
                    Spacer(modifier = Modifier.height(16.dp))
                    Text("Transferring to watch...")
                }
                InstallPhase.INSTALLING -> {
                    CircularProgressIndicator()
                    Spacer(modifier = Modifier.height(16.dp))
                    Text("Installing on watch...")
                }
                InstallPhase.SUCCESS -> {
                    Text(
                        text = "Installed successfully",
                        style = MaterialTheme.typography.titleMedium
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Button(onClick = onSetActive) {
                        Text("Set as active")
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Button(onClick = onDone) {
                        Text("Done")
                    }
                }
                InstallPhase.ERROR -> {
                    Text(
                        text = "Installation failed",
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.error
                    )
                    if (errorMessage != null) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = errorMessage,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                    Spacer(modifier = Modifier.height(16.dp))
                    Button(onClick = onDone) {
                        Text("Back")
                    }
                }
            }
        }
    }
}
