package com.cccstudios.newmx

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.appcompat.app.AlertDialog

/**
 * Names of SharedPreferences entries. Centralized to avoid string-key drift.
 */
object SettingsKeys {
    const val FILE = "newmx_settings"
    const val INCLUDE_TABLE = "include_decode_table"
}

/**
 * Single place to copy text to the clipboard. Keeps activities clean and
 * gives us one spot to add the Android 13+ clipboard-sensitive-content
 * flag later if needed.
 */
object ClipboardHelper {
    fun copyToClipboard(context: Context, text: String) {
        val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val clip = ClipData.newPlainText("NewMx encoded", text)
        cm.setPrimaryClip(clip)
    }
}

/**
 * One-screen help dialog. Shows how to use PROCESS_TEXT — most users won't
 * discover this on their own.
 */
object HelpDialog {
    fun show(context: Context) {
        AlertDialog.Builder(context)
            .setTitle(R.string.help_dialog_title)
            .setMessage(R.string.help_dialog_body)
            .setPositiveButton(R.string.ok, null)
            .show()
    }
}
