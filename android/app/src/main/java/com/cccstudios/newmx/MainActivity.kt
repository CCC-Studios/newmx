package com.cccstudios.newmx

import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.cccstudios.newmx.codec.Codec
import com.cccstudios.newmx.databinding.ActivityMainBinding

/**
 * Settings + sample encoder + codec info.
 *
 * The app's "home" screen. Most users won't open it often after first setup
 * — the real interaction is PROCESS_TEXT in other apps.
 *
 * This screen lets the user:
 *   - See codec version and stats
 *   - Toggle "include decode table" setting
 *   - Try the codec on sample text
 *   - Read the instructions for using PROCESS_TEXT
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var codec: Codec

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Codec might still be preloading. getInstance() blocks if so —
        // worst case ~150ms. Show a spinner if it's slow.
        codec = Codec.getInstance(this)

        bindCodecInfo()
        bindSettings()
        bindSampleEncoder()
        bindHelpButton()
    }

    private fun bindCodecInfo() {
        binding.codecVersionText.text = getString(
            R.string.codec_version_value,
            codec.codecVersion,
            codec.numMappings
        )
    }

    private fun bindSettings() {
        val prefs = getSharedPreferences(SettingsKeys.FILE, MODE_PRIVATE)
        val includeTable = prefs.getBoolean(SettingsKeys.INCLUDE_TABLE, false)
        binding.includeTableSwitch.isChecked = includeTable

        binding.includeTableSwitch.setOnCheckedChangeListener { _, checked ->
            prefs.edit().putBoolean(SettingsKeys.INCLUDE_TABLE, checked).apply()
        }
    }

    private fun bindSampleEncoder() {
        binding.sampleInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun afterTextChanged(s: Editable?) {
                val input = s?.toString() ?: ""
                if (input.isBlank()) {
                    binding.sampleOutput.text = ""
                    binding.sampleStats.text = ""
                    return
                }
                try {
                    val result = codec.encodeDetailed(input)
                    binding.sampleOutput.text = result.encoded
                    binding.sampleStats.text = getString(
                        R.string.sample_stats_format,
                        input.length, result.encoded.length, result.replacements.size
                    )
                } catch (e: Throwable) {
                    binding.sampleOutput.text = getString(
                        R.string.error_encode_failed, e.message ?: "unknown"
                    )
                    binding.sampleStats.text = ""
                }
            }
        })

        binding.copyEncodedButton.setOnClickListener {
            val encoded = binding.sampleOutput.text.toString()
            if (encoded.isBlank()) {
                Toast.makeText(this, getString(R.string.nothing_to_copy), Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            val prefs = getSharedPreferences(SettingsKeys.FILE, MODE_PRIVATE)
            val full = if (prefs.getBoolean(SettingsKeys.INCLUDE_TABLE, false)) {
                "${codec.decodeTable}\n\n$encoded"
            } else {
                encoded
            }
            ClipboardHelper.copyToClipboard(this, full)
            Toast.makeText(this, getString(R.string.copied_to_clipboard), Toast.LENGTH_SHORT).show()
        }
    }

    private fun bindHelpButton() {
        binding.helpButton.setOnClickListener {
            HelpDialog.show(this)
        }
    }
}
