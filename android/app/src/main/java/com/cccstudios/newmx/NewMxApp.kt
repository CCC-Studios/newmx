package com.cccstudios.newmx

import android.app.Application
import com.cccstudios.newmx.codec.Codec
import kotlin.concurrent.thread

/**
 * Application class. One job: preload the codec on a background thread
 * during app startup so the first encode call doesn't pay the ~100ms
 * JSON-parse + regex-compile cost on the UI thread.
 *
 * If preload hasn't finished by the time PROCESS_TEXT fires, the activity
 * blocks briefly (call to getInstance is synchronized).
 */
class NewMxApp : Application() {
    override fun onCreate() {
        super.onCreate()
        thread(start = true, name = "newmx-codec-preload") {
            try {
                Codec.getInstance(this)
            } catch (e: Throwable) {
                // Codec couldn't preload (e.g. missing asset). The first
                // call to getInstance from an activity will retry and may
                // throw a more useful error there. Don't crash startup.
                android.util.Log.w("NewMx", "Codec preload failed", e)
            }
        }
    }
}
