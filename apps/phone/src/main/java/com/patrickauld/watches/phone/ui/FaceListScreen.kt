package com.patrickauld.watches.phone.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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
import com.patrickauld.watches.phone.data.FaceStatus

data class FaceSummary(
    val slug: String,
    val name: String,
    val latestVersion: String,
    val status: FaceStatus
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FaceListScreen(
    faces: List<FaceSummary>,
    onFaceClick: (String) -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Watch Faces") })
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            items(faces) { face ->
                FaceCard(face = face, onClick = { onFaceClick(face.slug) })
            }
        }
    }
}

@Composable
private fun FaceCard(face: FaceSummary, onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp)
            .clickable(onClick = onClick)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = face.name,
                    style = MaterialTheme.typography.titleMedium
                )
                Text(
                    text = "v${face.latestVersion}",
                    style = MaterialTheme.typography.bodySmall
                )
            }
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = when (face.status) {
                    FaceStatus.NOT_INSTALLED -> "Not installed"
                    FaceStatus.INSTALLED -> "Installed"
                    FaceStatus.UPDATE_AVAILABLE -> "Update available"
                },
                style = MaterialTheme.typography.labelSmall,
                color = when (face.status) {
                    FaceStatus.UPDATE_AVAILABLE -> MaterialTheme.colorScheme.primary
                    else -> MaterialTheme.colorScheme.onSurfaceVariant
                }
            )
        }
    }
}
