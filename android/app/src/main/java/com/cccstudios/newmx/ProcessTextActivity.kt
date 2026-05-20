package com.cccstudios.newmx

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import com.cccstudios.newmx.codec.Codec

/**
 * THE LOAD-BEARING FEATURE.
 *
 * This activity is invoked by Android when the user selects text in any app
 * and taps "NewMx" in the floating text-selection toolbar (PROCESS_TEXT
 * intent).
 *
 * Flow:
 *   1. User selects prompt text in ChatGPT app (or any app)
 *   2. Long-press → "NewMx" appears in toolbar
 *   3. User taps NewMx → Android sends PROCESS_TEXT intent here
 *   4. We encode the text using the codec
 *   5. We return the encoded text via EXTRA_PROCESS_TEXT
 *   6. Android replaces the selected text in the source app
 *
 * No UI shown (theme is translucent + finish() immediately).
 *
 * Read-only field handling:
 *   - If EXTRA_PROCESS_TEXT_READONLY is true, we cannot return text.
 *     In that case, fall back to copying to clipboard so the user can
 *     paste manually. Toast informs them.
 */
class ProcessTextActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val intent = intent ?: run { finish(); return }
        val selectedText: CharSequence? = intent.getCharSequenceExtra(
            Intent.EXTRA_PROCESS_TEXT
        )
        val isReadOnly = intent.getBooleanExtra(
            Intent.EXTRA_PROCESS_TEXT_READONLY, false
        )

        if (selectedText.isNullOrBlank()) {
            toast(getString(R.string.error_no_text_selected))
            finish()
            return
        }

        // Encode using the codec. Errors are caught and surfaced as toast
        // — the encoder should never throw on normal input, but defense in
        // depth is cheap.
        val encoded: String = try {
            val codec = Codec.getInstance(this)
            val prefs = getSharedPreferences(SettingsKeys.FILE, MODE_PRIVATE)
            val includeTable = prefs.getBoolean(SettingsKeys.INCLUDE_TABLE, false)

            if (includeTable) {
                codec.encodeWithTable(selectedText.toString())
            } else {
                codec.encode(selectedText.toString())
            }
        } catch (e: Throwable) {
            android.util.Log.e("NewMx", "Encode failed", e)
            toast(getString(R.string.error_encode_failed, e.message ?: "unknown"))
            finish()
            return
        }

        // If the field is read-only, return-via-intent won't replace text.
        // Fall back to clipboard.
        if (isReadOnly) {
            ClipboardHelper.copyToClipboard(this, encoded)
            toast(getString(R.string.encoded_copied_readonly))
            finish()
            return
        }

        // Normal case: return encoded text via intent so source app replaces it
        val result = Intent().apply {
            putExtra(Intent.EXTRA_PROCESS_TEXT, encoded)
        }
        setResult(RESULT_OK, result)
        finish()
    }

    private fun toast(msg: String) {
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
    }
}
