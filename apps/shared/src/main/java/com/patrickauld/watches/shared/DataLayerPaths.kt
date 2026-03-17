package com.patrickauld.watches.shared

/**
 * Shared constants for Wear Data Layer communication between phone and watch apps.
 *
 * Both apps must use identical paths for messages and channels to connect.
 * Changing a value here requires rebuilding both apps.
 */
object DataLayerPaths {
    /** ChannelClient path for transferring watch face APK bytes from phone to watch. */
    const val CHANNEL_WATCHFACE_APK = "/watchface/apk"

    /** MessageClient path for install/update status reports from watch to phone. */
    const val MESSAGE_INSTALL_STATUS = "/watchface/install-status"

    /** MessageClient path for install requests from phone to watch. */
    const val MESSAGE_REQUEST_INSTALL = "/watchface/request-install"

    /** MessageClient path for activation requests from phone to watch. */
    const val MESSAGE_REQUEST_ACTIVATE = "/watchface/request-activate"

    /** Capability name advertised by the watch companion app. */
    const val CAPABILITY_WATCH_COMPANION = "watch_companion"
}
