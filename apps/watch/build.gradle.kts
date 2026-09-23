plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.compose.compiler)
}

val keystorePath = providers.environmentVariable("WATCHES_KEYSTORE").orNull
val keystorePassword = providers.environmentVariable("WATCHES_KEYSTORE_PASSWORD").orNull
val keyAlias = providers.environmentVariable("WATCHES_KEY_ALIAS").orNull
val keyPassword = providers.environmentVariable("WATCHES_KEY_PASSWORD").orNull
val personalSigning = listOf(keystorePath, keystorePassword, keyAlias, keyPassword).all { !it.isNullOrBlank() }

android {
    namespace = "com.patrickauld.watches.companion"
    compileSdk = 36
    if (personalSigning) {
        signingConfigs.create("personal") {
            storeFile = file(keystorePath!!)
            storePassword = keystorePassword
            this.keyAlias = keyAlias
            this.keyPassword = keyPassword
        }
    }

    defaultConfig {
        applicationId = "com.patrickauld.watches.companion"
        minSdk = 36
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        debug {
            if (personalSigning) signingConfig = signingConfigs.getByName("personal")
        }
        release {
            isMinifyEnabled = true
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    buildFeatures {
        compose = true
    }
}

dependencies {
    implementation(project(":apps:shared"))
    implementation(libs.watchface.push)
    implementation(libs.play.services.wearable)
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.10.2")
    implementation(libs.wear.compose.material)
    implementation(libs.wear.compose.foundation)
    implementation(libs.activity.compose)
    implementation(libs.lifecycle.runtime.compose)
    implementation(libs.lifecycle.viewmodel.compose)
    implementation(libs.core.ktx)
}
