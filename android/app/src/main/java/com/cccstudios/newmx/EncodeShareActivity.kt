package com.cccstudios.newmx

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import com.cccstudios.newmx.codec.Codec

/**
 * Share-sheet target.
 *
 * Used when the user can't use PROCESS_TEXT (some apps' text selection
 * doesn't show it). They share text to NewMx instead → we encode → we copy
 * the encoded result to clipboard so they can paste it.
 *
 * Translucent — no UI, just a toast confirming the action.
 */
class EncodeShareActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val intent = intent ?: run { finish(); return }
        if (intent.action != Intent.ACTION_SEND) {
            finish()
            return
        }

        val text = intent.getCharSequenceExtra(Intent.EXTRA_TEXT)?.toString()
        if (text.isNullOrBlank()) {
            toast(getString(R.string.error_no_text_shared))
            finish()
            return
        }

        val encoded: String = try {
            val codec = Codec.getInstance(this)
            val prefs = getSharedPreferences(SettingsKeys.FILE, MODE_PRIVATE)
            val includeTable = prefs.getBoolean(SettingsKeys.INCLUDE_TABLE, false)

            if (includeTable) codec.encodeWithTable(text) else codec.encode(text)
        } catch (e: Throwable) {
            android.util.Log.e("NewMx", "Encode failed (share)", e)
            toast(getString(R.string.error_encode_failed, e.message ?: "unknown"))
            finish()
            return
        }

        ClipboardHelper.copyToClipboard(this, encoded)
        toast(getString(R.string.encoded_copied_share))
        finish()
    }

    private fun toast(msg: String) {
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
    }
}
