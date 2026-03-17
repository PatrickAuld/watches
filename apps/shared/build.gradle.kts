plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.patrickauld.watches.shared"
    compileSdk = 36

    defaultConfig {
        minSdk = 30
    }
}
