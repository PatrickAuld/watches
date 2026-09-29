plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.compose.compiler)
}

val keystorePath = providers.environmentVariable("WATCHES_KEYSTORE").orNull
val keystorePassword = providers.environmentVariable("WATCHES_KEYSTORE_PASSWORD").orNull
val keyAlias = providers.environmentVariable("WATCHES_KEY_ALIAS").orNull
val keyPassword = providers.environmentVariable("WATCHES_KEY_PASSWORD").orNull
val personalSigning = listOf(keystorePath, keystorePassword, keyAlias, keyPassword).all { !it.isNullOrBlank() }
val playUploadKeystorePath = providers.environmentVariable("PLAY_UPLOAD_KEYSTORE").orNull
val playUploadKeystorePassword = providers.environmentVariable("PLAY_UPLOAD_KEYSTORE_PASSWORD").orNull
val playUploadKeyAlias = providers.environmentVariable("PLAY_UPLOAD_KEY_ALIAS").orNull
val playUploadKeyPassword = providers.environmentVariable("PLAY_UPLOAD_KEY_PASSWORD").orNull
val playUploadSigning = listOf(
    playUploadKeystorePath,
    playUploadKeystorePassword,
    playUploadKeyAlias,
    playUploadKeyPassword
).all { !it.isNullOrBlank() }
val releaseTaskRequested = gradle.startParameter.taskNames.any { it.contains("Release") }

if (releaseTaskRequested && !playUploadSigning) {
    throw GradleException("Set PLAY_UPLOAD_KEYSTORE, PLAY_UPLOAD_KEYSTORE_PASSWORD, PLAY_UPLOAD_KEY_ALIAS, and PLAY_UPLOAD_KEY_PASSWORD to build a release bundle")
}

val playVersionCode = providers.gradleProperty("playVersionCode").orElse("1").get().toIntOrNull()
    ?: throw GradleException("playVersionCode must be an integer")
val playVersionName = providers.gradleProperty("playVersionName").orElse("0.1.0").get()

android {
    namespace = "com.patrickauld.watches.phone"
    compileSdk = 36
    if (personalSigning) {
        signingConfigs.create("personal") {
            storeFile = file(keystorePath!!)
            storePassword = keystorePassword
            this.keyAlias = keyAlias
            this.keyPassword = keyPassword
        }
    }
    if (playUploadSigning) {
        signingConfigs.create("playUpload") {
            storeFile = file(playUploadKeystorePath!!)
            storePassword = playUploadKeystorePassword
            this.keyAlias = playUploadKeyAlias
            this.keyPassword = playUploadKeyPassword
        }
    }

    defaultConfig {
        applicationId = "com.patrickauld.watches.companion"
        minSdk = 30
        targetSdk = 36
        versionCode = playVersionCode
        versionName = playVersionName
    }

    buildTypes {
        debug {
            if (personalSigning) signingConfig = signingConfigs.getByName("personal")
        }
        release {
            isMinifyEnabled = true
            if (playUploadSigning) signingConfig = signingConfigs.getByName("playUpload")
        }
    }

    buildFeatures {
        compose = true
    }
}

dependencies {
    implementation(project(":apps:shared"))
    implementation(libs.play.services.wearable)
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.10.2")
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.material3)
    implementation(libs.compose.ui.tooling.preview)
    implementation(libs.activity.compose)
    implementation(libs.lifecycle.runtime.compose)
    implementation(libs.lifecycle.viewmodel.compose)
    implementation(libs.core.ktx)
    implementation(libs.work.runtime)
}
