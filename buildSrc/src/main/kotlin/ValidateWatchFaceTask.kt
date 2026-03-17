import org.gradle.api.DefaultTask
import org.gradle.api.file.RegularFileProperty
import org.gradle.api.tasks.InputFile
import org.gradle.api.tasks.OutputFile
import org.gradle.api.tasks.TaskAction

/**
 * Custom Gradle task that validates a watch face APK and produces a validation token.
 *
 * This task wraps the `validator-push` library. The validator-push dependency
 * is deferred until the library is stable and available on Maven/JitPack.
 * For now, this task copies the APK path to a token placeholder file so the
 * rest of the pipeline can be wired up.
 *
 * TODO: Replace stub with actual validator-push invocation when the library
 * is available. See: https://developer.android.com/training/wearables/wff/push
 */
abstract class ValidateWatchFaceTask : DefaultTask() {

    @get:InputFile
    abstract val apkFile: RegularFileProperty

    @get:OutputFile
    abstract val tokenFile: RegularFileProperty

    @TaskAction
    fun validate() {
        val apk = apkFile.get().asFile
        val token = tokenFile.get().asFile

        logger.lifecycle("Validating watch face APK: ${apk.absolutePath}")

        // Stub: write a placeholder token file.
        // When validator-push is available, this will:
        // 1. Run the validator against the APK
        // 2. Write the signed validation token to tokenFile
        token.writeText("PLACEHOLDER_TOKEN:${apk.name}:${System.currentTimeMillis()}")

        logger.lifecycle("Validation token written to: ${token.absolutePath}")
    }
}
