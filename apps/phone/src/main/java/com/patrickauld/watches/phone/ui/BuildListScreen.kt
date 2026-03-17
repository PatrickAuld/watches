package com.patrickauld.watches.phone.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.patrickauld.watches.phone.data.AvailableBuild

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BuildListScreen(
    faceName: String,
    builds: List<AvailableBuild>,
    installedVersionCode: Int?,
    onInstallClick: (AvailableBuild) -> Unit,
    onBack: () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(title = { Text(faceName) })
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            items(builds) { build ->
                BuildCard(
                    build = build,
                    isInstalled = installedVersionCode == build.versionCode,
                    onInstallClick = { onInstallClick(build) }
                )
            }
        }
    }
}

@Composable
private fun BuildCard(
    build: AvailableBuild,
    isInstalled: Boolean,
    onInstallClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "v${build.versionName} (${build.buildType})",
                    style = MaterialTheme.typography.titleSmall
                )
                Text(
                    text = "${build.commitSha.take(7)} - ${build.timestamp}",
                    style = MaterialTheme.typography.bodySmall
                )
            }
            if (isInstalled) {
                Text(
                    text = "Installed",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            } else {
                Button(onClick = onInstallClick) {
                    Text("Install")
                }
            }
        }
    }
}
