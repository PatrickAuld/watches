import org.gradle.api.DefaultTask
import org.gradle.api.file.DirectoryProperty
import org.gradle.api.file.RegularFileProperty
import org.gradle.api.provider.Property
import org.gradle.api.tasks.Input
import org.gradle.api.tasks.InputDirectory
import org.gradle.api.tasks.InputFile
import org.gradle.api.tasks.Optional
import org.gradle.api.tasks.OutputDirectory
import org.gradle.api.tasks.TaskAction

plugins {
    alias(libs.plugins.android.application)
}

abstract class StageWatchFace : DefaultTask() {
    @get:InputFile abstract val xml: RegularFileProperty
    @get:InputDirectory @get:Optional abstract val assets: DirectoryProperty
    @get:Input abstract val faceSlug: Property<String>
    @get:OutputDirectory abstract val outputDir: DirectoryProperty

    @TaskAction
    fun stage() {
        val output = outputDir.get().asFile
        output.deleteRecursively()
        val raw = output.resolve("raw").apply { mkdirs() }
        xml.get().asFile.copyTo(raw.resolve("watchface.xml"))
        if (assets.isPresent) {
            assets.get().asFile.copyRecursively(output.resolve("drawable"))
        }
        val displayName = faceSlug.get().split('-').joinToString(" ") {
            it.replaceFirstChar(Char::uppercaseChar)
        }
        output.resolve("values").apply { mkdirs() }.resolve("strings.xml")
            .writeText("<resources><string name=\"watch_face_name\">$displayName</string></resources>\n")
    }
}

val slug = providers.gradleProperty("faceSlug").orElse("sundial").get()
require(Regex("[a-z][a-z0-9-]*").matches(slug)) { "Invalid faceSlug: $slug" }
val faceDir = rootProject.file("faces/$slug")
val faceXml = faceDir.resolve("watchface.xml")
require(faceXml.isFile) { "Missing canonical XML: $faceXml" }

val keystorePath = providers.environmentVariable("WATCHES_KEYSTORE").orNull
val keystorePassword = providers.environmentVariable("WATCHES_KEYSTORE_PASSWORD").orNull
val keyAlias = providers.environmentVariable("WATCHES_KEY_ALIAS").orNull
val keyPassword = providers.environmentVariable("WATCHES_KEY_PASSWORD").orNull
val personalSigning = listOf(keystorePath, keystorePassword, keyAlias, keyPassword).all { !it.isNullOrBlank() }

android {
    enableKotlin = false
    namespace = "com.patrickauld.watches.face"
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

androidComponents.onVariants { variant ->
    val stage = tasks.register<StageWatchFace>("stage${variant.name.replaceFirstChar(Char::uppercaseChar)}WatchFace") {
        xml.set(faceXml)
        val assetDir = faceDir.resolve("assets")
        if (assetDir.isDirectory) assets.set(assetDir)
        faceSlug.set(slug)
        outputDir.set(layout.buildDirectory.dir("generated/wff/${variant.name}/res"))
    }
    variant.sources.res?.addGeneratedSourceDirectory(stage, StageWatchFace::outputDir)
}
