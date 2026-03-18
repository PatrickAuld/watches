plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.patrickauld.watches.shared"
    compileSdk = 36

    defaultConfig {
        minSdk = 30
    }
}
