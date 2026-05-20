package com.cccstudios.newmx.codec

/**
 * Decode-table preamble builder.
 *
 * Mirror of Python newmx/_decoder.py::build_decode_table.
 *
 * Produces the ~3,850-token preamble that gets prepended to encoded prompts.
 * Tells the receiving LLM how to interpret each glyph.
 *
 * IMPORTANT: this is the dominant fixed cost of Path 1. ~4,000 tokens up
 * front. Path 1 is best for sessions, agent loops, or with prompt-caching.
 */
object DecodeTable {

    /**
     * Build the full decode-table preamble for the given codec map.
     *
     * Output is deterministic (given the same map, same string out).
     * Cache this string on the Codec instance — building it is O(N) over
     * map entries, ~1-5ms.
     */
    fun build(map: PhraseGlyphMap): String {
        // Group entries by family glyph; structural entries are 1-to-1
        val byFamily = mutableMapOf<String, MutableList<PhraseGlyphMap.Entry>>()
        val structural = mutableMapOf<String, String>()  // glyph -> phrase

        for (entry in map.entries) {
            if (entry.family in CodecConstants.INTENT_FAMILIES) {
                byFamily.getOrPut(entry.family) { mutableListOf() }.add(entry)
            } else {
                // Structural is 1-to-1 — first wins if there are dupes (there shouldn't be)
                structural.putIfAbsent(entry.glyph, entry.phrase)
            }
        }

        val sb = StringBuilder(10_000)
        sb.append("=".repeat(60)).append('\n')
        sb.append("NewMx赤 Path 1 — Decode table for this session").append('\n')
        sb.append("=".repeat(60)).append('\n')
        sb.append('\n')
        sb.append("I will use single-character glyphs to compress prompts.").append('\n')
        sb.append("Decode each glyph below to its meaning before answering.").append('\n')
        sb.append('\n')
        sb.append("FAMILY GLYPHS (").append(byFamily.size).append(") — semantic intent compression:\n")
        sb.append("Each glyph stands for the family of related phrases listed.\n")
        sb.append("Treat any of the listed phrases (or close variants) as equivalent.\n")
        sb.append('\n')

        // Sorted by family name for stable output
        for (family in byFamily.keys.sorted()) {
            val phrases = byFamily[family]!!.sortedBy { it.phrase.length }
            val rep = phrases.first()
            val count = phrases.size
            sb.append("  ").append(rep.glyph).append(" = ").append(family)
                .append(" (e.g. \"").append(rep.phrase).append("\"")
            if (count > 1) {
                sb.append(", and ").append(count - 1).append(" similar")
            }
            sb.append(")\n")
        }

        sb.append('\n')
        sb.append("STRUCTURAL GLYPHS (").append(structural.size).append(") — exact phrase substitution:\n")
        sb.append("Replace each glyph with its phrase verbatim.\n")
        sb.append('\n')

        // Group by 5 per row, sorted by phrase
        val structSorted = structural.entries.sortedBy { it.value }
        val rowBuf = mutableListOf<String>()
        for ((glyph, phrase) in structSorted) {
            rowBuf.add("$glyph='$phrase'")
            if (rowBuf.size == 5) {
                sb.append("  ").append(rowBuf.joinToString("  ")).append('\n')
                rowBuf.clear()
            }
        }
        if (rowBuf.isNotEmpty()) {
            sb.append("  ").append(rowBuf.joinToString("  ")).append('\n')
        }

        sb.append('\n')
        sb.append("=".repeat(60)).append('\n')
        sb.append("END decode table. The encoded prompts will follow.\n")
        sb.append("=".repeat(60))

        return sb.toString()
    }

    /**
     * Build a glyph → (canonical phrase, family) reverse map used by decode().
     */
    fun buildDecodeMap(map: PhraseGlyphMap): Map<String, Pair<String, String>> {
        val out = mutableMapOf<String, Pair<String, String>>()
        for (entry in map.entries) {
            if (entry.glyph in out) continue  // first wins (canonical for families)
            out[entry.glyph] = entry.phrase to entry.family
        }
        return out
    }

    /**
     * Decode encoded text by replacing each glyph with its canonical phrase.
     *
     * Lossy for family glyphs (returns canonical, not original phrase variant).
     * Structural glyphs round-trip exactly.
     */
    fun decode(encoded: String, decodeMap: Map<String, Pair<String, String>>): String {
        val sb = StringBuilder(encoded.length * 2)
        for (ch in encoded) {
            val key = ch.toString()
            val entry = decodeMap[key]
            if (entry != null) {
                sb.append(entry.first)
            } else {
                sb.append(ch)
            }
        }
        return sb.toString()
    }
}
