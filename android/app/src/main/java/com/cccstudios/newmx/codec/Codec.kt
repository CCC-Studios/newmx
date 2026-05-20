package com.cccstudios.newmx.codec

import android.content.Context

/**
 * Public façade for the NewMx Path 1 codec.
 *
 * Mirrors Python `newmx.Codec` API:
 *   - encode(text)              → encoded text, no decode table
 *   - encodeWithTable(text)     → decode table preamble + encoded text
 *   - decode(text)              → reverse direction (lossy for families)
 *   - encodeDetailed(text)      → EncodingResult with diagnostics
 *
 * Codec instances are heavy (loads ~310KB JSON, compiles 2 large regexes).
 * Build ONCE per process and reuse via Codec.getInstance(context).
 *
 * Thread-safety: encodings are stateless; the codec can be used from any
 * thread once constructed.
 */
class Codec private constructor(
    private val map: PhraseGlyphMap,
    private val compiled: CompiledPatterns
) {
    private val decodeMap: Map<String, Pair<String, String>> by lazy {
        DecodeTable.buildDecodeMap(map)
    }

    private val cachedDecodeTable: String by lazy {
        DecodeTable.build(map)
    }

    /** Codec version string (e.g. "v005-rev4"). */
    val codecVersion: String get() = map.version

    /** Total phrase mappings in the codec (e.g. 3,135). */
    val numMappings: Int get() = map.size

    /** Decode-table preamble. Cached; built lazily on first access. */
    val decodeTable: String get() = cachedDecodeTable

    /**
     * Encode text. Multi-line input is encoded per-line. Code-detected lines
     * are returned unchanged.
     *
     * Returns just the encoded text — for the production-ready LLM prompt
     * (including decode table), call encodeWithTable().
     */
    fun encode(text: String): String {
        if (text.isEmpty()) return text
        return encodeDetailed(text).encoded
    }

    /**
     * Encode text and prepend the decode-table preamble. This is what you
     * send to the LLM.
     */
    fun encodeWithTable(text: String): String {
        return "$decodeTable\n\n${encode(text)}"
    }

    /**
     * Decode encoded text back to canonical phrase form.
     *
     * NOTE: family glyphs decode to canonical representative, not original
     * input phrase. Path 1 is intent-preserving, not byte-exact.
     */
    fun decode(encoded: String): String {
        return DecodeTable.decode(encoded, decodeMap)
    }

    /**
     * Encode with diagnostic info.
     */
    fun encodeDetailed(text: String): EncodingResult {
        if (text.isEmpty()) {
            return EncodingResult(text, text, text, emptyList(), isCode = false)
        }
        if ('\n' in text) {
            // Multi-line: encode each line independently, concat results
            val lines = text.split('\n')
            val results = lines.map { encodeOneLine(it) }
            return EncodingResult(
                raw = lines.joinToString("\n") { it },
                normalized = results.joinToString("\n") { it.normalized },
                encoded = results.joinToString("\n") { it.encoded },
                replacements = results.flatMap { it.replacements },
                isCode = results.any { it.isCode }
            )
        }
        return encodeOneLine(text)
    }

    private fun encodeOneLine(line: String): EncodingResult {
        if (Normalizer.isCodeLine(line)) {
            return EncodingResult(line, line, line, emptyList(), isCode = true)
        }
        val normalized = Normalizer.normalizeLine(line)
        val (encoded, reps) = Encoder.encodeLine(normalized, compiled).let { it.encoded to it.replacements }
        return EncodingResult(line, normalized, encoded, reps, isCode = false)
    }

    /**
     * Diagnostic result of one encode operation.
     */
    data class EncodingResult(
        val raw: String,
        val normalized: String,
        val encoded: String,
        val replacements: List<Encoder.Replacement>,
        val isCode: Boolean
    )

    companion object {
        private const val ASSET_NAME = "path1_en_b3_v005_rev4.json"

        @Volatile
        private var INSTANCE: Codec? = null

        /**
         * Get or build the codec singleton. Application context preferred to
         * avoid Activity leaks.
         *
         * First call: ~50-150ms (JSON parse + regex compile).
         * Subsequent calls: instant.
         */
        fun getInstance(context: Context): Codec {
            INSTANCE?.let { return it }
            synchronized(this) {
                INSTANCE?.let { return it }
                val built = buildFromAsset(context.applicationContext)
                INSTANCE = built
                return built
            }
        }

        /**
         * Build the codec from the bundled JSON asset. Visible for tests.
         */
        fun buildFromAsset(context: Context): Codec {
            val jsonText = context.assets.open(ASSET_NAME).bufferedReader(Charsets.UTF_8).use {
                it.readText()
            }
            return buildFromJsonString(jsonText)
        }

        /**
         * Build the codec from a JSON string. Used by unit tests with a
         * synthetic minimal map.
         */
        fun buildFromJsonString(jsonText: String): Codec {
            val map = PhraseGlyphMap.fromJson(jsonText)
            val compiled = Encoder.compilePatterns(map)
            return Codec(map, compiled)
        }
    }
}
