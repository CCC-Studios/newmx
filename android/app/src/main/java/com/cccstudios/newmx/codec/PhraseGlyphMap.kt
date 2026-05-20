package com.cccstudios.newmx.codec

import org.json.JSONObject

/**
 * In-memory representation of the codec's phrase→glyph map.
 *
 * Loaded once at app startup from the bundled JSON asset
 * (path1_en_b3_v005_rev4.json, ~310KB). Same schema as Python's bundled map.
 *
 * JSON schema:
 * {
 *   "meta": { "version": "v005-rev4", ... },
 *   "phrase_to_family_and_glyph": {
 *     "how to":  { "family": "HOW_TO_PROCEDURE", "glyph": "µ" },
 *     "in the":  { "family": "STRUCTURAL_BIGRAM", "glyph": "Ñ" },
 *     ...
 *   }
 * }
 */
class PhraseGlyphMap(
    val version: String,
    val entries: List<Entry>
) {
    data class Entry(
        val phrase: String,
        val family: String,
        val glyph: String
    )

    /** Total mappings (e.g. 3,135 for v005-rev4). */
    val size: Int get() = entries.size

    /** Number of unique family glyphs (e.g. 38). */
    fun familyGlyphCount(): Int =
        entries.filter { it.family in CodecConstants.INTENT_FAMILIES }
            .map { it.glyph }.distinct().size

    /** Number of unique structural glyphs (e.g. 419). */
    fun structuralGlyphCount(): Int =
        entries.filter { it.family !in CodecConstants.INTENT_FAMILIES }
            .map { it.glyph }.distinct().size

    companion object {
        /**
         * Parse a phrase-glyph-map JSON string.
         *
         * Tolerant of missing meta.version (defaults to "unknown").
         */
        fun fromJson(jsonText: String): PhraseGlyphMap {
            val root = JSONObject(jsonText)

            val version = root.optJSONObject("meta")?.optString("version", "unknown")
                ?: "unknown"

            val phraseObj = root.getJSONObject("phrase_to_family_and_glyph")
            val entries = mutableListOf<Entry>()

            val keys = phraseObj.keys()
            while (keys.hasNext()) {
                val phrase = keys.next()
                val info = phraseObj.getJSONObject(phrase)
                val family = info.getString("family")
                val glyph = info.getString("glyph")
                entries.add(Entry(phrase, family, glyph))
            }

            return PhraseGlyphMap(version, entries)
        }
    }
}
