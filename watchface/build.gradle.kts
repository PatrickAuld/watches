plugins {
    alias(libs.plugins.android.application)
}

val slug = providers.gradleProperty("faceSlug").orElse("sundial").get()
require(Regex("[a-z][a-z0-9-]*").matches(slug)) { "Invalid faceSlug: $slug" }
val faceDir = rootProject.file("faces/$slug")
val faceXml = faceDir.resolve("watchface.xml")
require(faceXml.isFile) { "Missing canonical XML: $faceXml" }
val generatedRes = layout.buildDirectory.dir("generated/wff/res")

val stageWatchFace by tasks.registering {
    inputs.file(faceXml)
    inputs.dir(faceDir.resolve("assets")).optional()
    outputs.dir(generatedRes)
    doLast {
        val output = generatedRes.get().asFile
        output.deleteRecursively()
        val raw = output.resolve("raw").apply { mkdirs() }
        faceXml.copyTo(raw.resolve("watchface.xml"))
        val assets = faceDir.resolve("assets")
        if (assets.exists()) {
            project.copy { from(assets); into(output.resolve("drawable")) }
        }
        val displayName = slug.split('-').joinToString(" ") { it.replaceFirstChar(Char::uppercaseChar) }
        output.resolve("values").apply { mkdirs() }.resolve("strings.xml")
            .writeText("<resources><string name=\"watch_face_name\">$displayName</string></resources>\n")
    }
}

val keystorePath = providers.environmentVariable("WATCHES_KEYSTORE").orNull
val keystorePassword = providers.environmentVariable("WATCHES_KEYSTORE_PASSWORD").orNull
val keyAlias = providers.environmentVariable("WATCHES_KEY_ALIAS").orNull
val keyPassword = providers.environmentVariable("WATCHES_KEY_PASSWORD").orNull
val personalSigning = listOf(keystorePath, keystorePassword, keyAlias, keyPassword).all { !it.isNullOrBlank() }

tasks.named("preBuild") { dependsOn(stageWatchFace) }

android {
    enableKotlin = false
    namespace = "com.patrickauld.watches.face"
    compileSdk = 36
    sourceSets.getByName("main").res.srcDir(generatedRes)
    if (personalSigning) {
        signingConfigs.create("personal") {
            storeFile = file(keystorePath!!)
            storePassword = keystorePassword
            this.keyAlias = keyAlias
            this.keyPassword = keyPassword
        }
    }

    defaultConfig {
        applicationId = "com.patrickauld.watches.companion.watchfacepush.${slug.replace('-', '_')}"
        minSdk = 36
        targetSdk = 36
        versionCode = providers.environmentVariable("GITHUB_RUN_NUMBER").orElse("1").get().toInt()
        versionName = "0.1.$versionCode"
    }

    buildTypes {
        debug {
            if (personalSigning) signingConfig = signingConfigs.getByName("personal")
        }
        release { isMinifyEnabled = false }
    }
}
