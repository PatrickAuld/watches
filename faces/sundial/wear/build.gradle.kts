plugins {
    alias(libs.plugins.android.application)
}

// Copy canonical WFF XML and assets into the WearOS resource directories.
// The source of truth lives at faces/sundial/watchface.xml and faces/sundial/assets/.
val copyWatchFaceXml by tasks.registering(Copy::class) {
    from(rootProject.file("faces/sundial/watchface.xml"))
    into(layout.projectDirectory.dir("src/main/res/raw"))
}

val copyWatchFaceAssets by tasks.registering(Copy::class) {
    from(rootProject.file("faces/sundial/assets"))
    into(layout.projectDirectory.dir("src/main/res/drawable"))
}

tasks.named("preBuild") {
    dependsOn(copyWatchFaceXml, copyWatchFaceAssets)
}

android {
    enableKotlin = false
    namespace = "com.patrickauld.watches.sundial"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.patrickauld.watches.companion.watchfacepush.sundial"
        minSdk = 36
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        debug {
            isMinifyEnabled = true
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}
