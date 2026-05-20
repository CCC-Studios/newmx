package com.cccstudios.newmx.codec

import java.util.regex.Pattern

/**
 * Pre-compiled regex artifacts for fast encoding. Build once per codec, reuse.
 *
 * Mirrors Python newmx/_encoder.py::CompiledPatterns.
 *
 * Patterns held here are stateless and thread-safe (java.util.regex.Pattern
 * is immutable; Matchers are not, but we create one per call).
 */
data class CompiledPatterns(
    val familyPattern: Pattern? = null,
    val familyDispatch: Map<String, FamilyEntry> = emptyMap(),
    val structuralPattern: Pattern? = null,
    val structuralDispatch: Map<String, String> = emptyMap(),
    val orphanSuffixPattern: Pattern? = null,
    val preglyphSpacePattern: Pattern? = null,
    val familyGlyphClass: String = "",
    val allGlyphClass: String = ""
) {
    data class FamilyEntry(val family: String, val glyph: String)
}

/**
 * Encoder — Kotlin port of newmx/_encoder.py.
 *
 * Logic mirror is exact:
 *   1. Family pass (fixed-point iteration, boundary-aware)
 *   2. Orphan-suffix-after-glyph strip (rev4)
 *   3. Structural pass
 *   4. Pre-glyph-space strip (cli5)
 *
 * IMPORTANT REGEX DIFFERENCES:
 *   - Python case-insensitive matching of non-ASCII works with re.IGNORECASE +
 *     re.UNICODE. Java equivalent: Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE.
 *   - Pattern.compile is happy with the same regex syntax as Python re for our
 *     use cases (alternation, lookbehind, char classes).
 *
 * NB: variable-width lookbehind is needed because of the boundary_lookbehind
 * structure ("|^|(?<=[.!?:;,\\n])|(?<=[GLYPHS])|(?<=\\band\\s)|(?<=\\bor\\s)..."
 * which has alternatives of different widths). Java's regex engine supports
 * this since Java 9 via the (?<=...) variable-width syntax with bounded
 * alternation. Verified: \b<conj>\s is bounded (max 5 chars: "then "), so OK.
 */
object Encoder {

    /**
     * Build the family glyph character class (used in boundary lookbehind).
     *
     * Returns a string containing all distinct family-layer glyph characters,
     * each regex-escaped. Same filtering as Python:
     *   - Family-layer entries only
     *   - Single-character glyphs only
     *   - Skip ASCII A-Za-z (would break \b semantics)
     */
    private fun buildFamilyGlyphClass(map: PhraseGlyphMap): String {
        val glyphs = sortedSetOf<String>()
        for (entry in map.entries) {
            if (entry.family !in CodecConstants.INTENT_FAMILIES) continue
            val g = entry.glyph
            if (g.length != 1) continue
            val c = g[0]
            if (c in 'A'..'Z' || c in 'a'..'z') continue
            glyphs.add(g)
        }
        return glyphs.joinToString("") { Pattern.quote(it).removeSurrounding("\\Q", "\\E").let { s -> regexEscapeChar(s) } }
    }

    /**
     * Build the "all glyph" character class (used by cli5 pre-glyph-space).
     *
     * Same as family class but includes structural glyphs too.
     */
    private fun buildAllGlyphClass(map: PhraseGlyphMap): String {
        val glyphs = sortedSetOf<String>()
        for (entry in map.entries) {
            val g = entry.glyph
            if (g.length != 1) continue
            val c = g[0]
            if (c in 'A'..'Z' || c in 'a'..'z') continue
            glyphs.add(g)
        }
        return glyphs.joinToString("") { regexEscapeChar(it) }
    }

    /**
     * Regex-escape a single character for inclusion in a character class.
     * Inside [...], only \, ], ^, - need escaping; everything else is literal.
     */
    private fun regexEscapeChar(s: String): String {
        if (s.length != 1) return Pattern.quote(s)
        return when (s[0]) {
            '\\', ']', '^', '-' -> "\\$s"
            else -> s
        }
    }

    /**
     * Regex-escape a multi-character phrase for use in an alternation.
     * Equivalent to Python's re.escape(): escapes anything that's a regex metachar.
     */
    private fun regexEscapePhrase(s: String): String {
        val sb = StringBuilder(s.length + 4)
        for (c in s) {
            when (c) {
                '\\', '.', '+', '*', '?', '(', ')', '|', '[', ']', '{', '}',
                '^', '$', '#', '&', '-', '~' -> sb.append('\\').append(c)
                else -> sb.append(c)
            }
        }
        return sb.toString()
    }

    /**
     * Compile all patterns. Run once per codec load (~50-100ms on first call,
     * then cached on the codec instance).
     */
    fun compilePatterns(map: PhraseGlyphMap): CompiledPatterns {
        val familyClass = buildFamilyGlyphClass(map)
        val allClass = buildAllGlyphClass(map)

        // ---- Family-boundary lookbehind ----
        // Matches: line start, sentence-ender, any family glyph, or
        // conjunction + whitespace.
        val boundaryParts = mutableListOf<String>()
        boundaryParts.add("^")
        boundaryParts.add("(?<=[.!?:;,\\n])")
        if (familyClass.isNotEmpty()) {
            boundaryParts.add("(?<=[$familyClass])")
        }
        for (conj in CodecConstants.FAMILY_BOUNDARY_CONJUNCTIONS) {
            // Variable-width lookbehind. Bounded (conj+space = max 5 chars),
            // accepted by Java regex engine.
            boundaryParts.add("(?<=\\b$conj\\s)")
        }
        val boundaryLookbehind = "(?:" + boundaryParts.joinToString("|") + ")"

        // ---- Sort entries longest-first ----
        // Critical: "tell me what you find" must match before "tell me".
        // Tiebreaker on char length keeps order deterministic.
        val entries = map.entries
            .filter { it.phrase !in CodecConstants.BANNED_FAMILY_PHRASES }
            .sortedWith(
                compareByDescending<PhraseGlyphMap.Entry> { it.phrase.split(' ').size }
                    .thenByDescending { it.phrase.length }
            )

        // ---- Partition family vs structural ----
        val familyEntries = entries.filter { it.family in CodecConstants.INTENT_FAMILIES }
        val structEntries = entries.filter { it.family !in CodecConstants.INTENT_FAMILIES }

        // ---- Family alternation ----
        var familyPattern: Pattern? = null
        val familyDispatch = mutableMapOf<String, CompiledPatterns.FamilyEntry>()
        if (familyEntries.isNotEmpty()) {
            val alt = familyEntries.joinToString("|") { regexEscapePhrase(it.phrase) }
            val patternStr = boundaryLookbehind + "\\s*(" + alt + ")\\b"
            familyPattern = Pattern.compile(
                patternStr,
                Pattern.CASE_INSENSITIVE or Pattern.UNICODE_CASE
            )
            for (e in familyEntries) {
                familyDispatch[e.phrase.lowercase()] = CompiledPatterns.FamilyEntry(e.family, e.glyph)
            }
        }

        // ---- Structural alternation ----
        var structuralPattern: Pattern? = null
        val structuralDispatch = mutableMapOf<String, String>()
        if (structEntries.isNotEmpty()) {
            val alt = structEntries.joinToString("|") { regexEscapePhrase(it.phrase) }
            structuralPattern = Pattern.compile(
                "\\b(" + alt + ")\\b",
                Pattern.CASE_INSENSITIVE or Pattern.UNICODE_CASE
            )
            for (e in structEntries) {
                structuralDispatch[e.phrase.lowercase()] = e.glyph
            }
        }

        // ---- Orphan-suffix-after-glyph (rev4) ----
        var orphanSuffix: Pattern? = null
        if (familyClass.isNotEmpty()) {
            orphanSuffix = Pattern.compile(
                "([$familyClass])\\s+(?:for|to|with)\\s+me\\b",
                Pattern.CASE_INSENSITIVE or Pattern.UNICODE_CASE
            )
        }

        // ---- Pre-glyph-space (cli5) ----
        var preglyphSpace: Pattern? = null
        if (allClass.isNotEmpty()) {
            preglyphSpace = Pattern.compile("\\s+([$allClass])")
        }

        return CompiledPatterns(
            familyPattern = familyPattern,
            familyDispatch = familyDispatch,
            structuralPattern = structuralPattern,
            structuralDispatch = structuralDispatch,
            orphanSuffixPattern = orphanSuffix,
            preglyphSpacePattern = preglyphSpace,
            familyGlyphClass = familyClass,
            allGlyphClass = allClass
        )
    }

    /**
     * Replacement record (mirror of Python's dict).
     */
    data class Replacement(
        val family: String,
        val phrase: String,
        val matched: String,
        val glyph: String
    )

    data class EncodeResult(
        val encoded: String,
        val replacements: List<Replacement>
    )

    /**
     * Encode one pre-normalized line.
     *
     * Returns (encoded_text, replacements_list).
     *
     * Family pass iterates to a fixed point (max 4 passes, same as Python).
     */
    fun encodeLine(line: String, cp: CompiledPatterns): EncodeResult {
        var text = line
        val reps = mutableListOf<Replacement>()

        // Family pass — fixed-point iteration
        if (cp.familyPattern != null && cp.familyPattern.matcher(text).find()) {
            for (pass in 0 until 4) {
                val before = text
                text = replaceAll(cp.familyPattern, text) { match ->
                    val matched = match.group(1) ?: return@replaceAll match.group()!!
                    val entry = cp.familyDispatch[matched.lowercase()] ?: return@replaceAll matched
                    reps.add(Replacement(entry.family, matched.lowercase(), matched, entry.glyph))
                    entry.glyph
                }
                if (text == before) break
            }
        }

        // Orphan-suffix-after-glyph (rev4)
        if (cp.orphanSuffixPattern != null) {
            text = cp.orphanSuffixPattern.matcher(text).replaceAll("$1")
        }

        // Structural pass
        if (cp.structuralPattern != null) {
            text = replaceAll(cp.structuralPattern, text) { match ->
                val matched = match.group(1) ?: return@replaceAll match.group()!!
                val glyph = cp.structuralDispatch[matched.lowercase()] ?: return@replaceAll matched
                reps.add(Replacement("STRUCTURAL", matched.lowercase(), matched, glyph))
                glyph
            }
        }

        // Pre-glyph-space (cli5)
        if (cp.preglyphSpacePattern != null) {
            text = cp.preglyphSpacePattern.matcher(text).replaceAll("$1")
        }

        return EncodeResult(text, reps)
    }

    /**
     * Helper: scan and replace with a function (mirror of Python re.sub with callback).
     *
     * Necessary because Java's Matcher.appendReplacement does $-substitution that
     * would mangle replacement strings containing literal $ or \.
     */
    private inline fun replaceAll(
        pattern: Pattern,
        text: String,
        replacement: (java.util.regex.MatchResult) -> String
    ): String {
        val m = pattern.matcher(text)
        val sb = StringBuilder(text.length)
        var last = 0
        while (m.find()) {
            sb.append(text, last, m.start())
            sb.append(replacement(m.toMatchResult()))
            last = m.end()
        }
        sb.append(text, last, text.length)
        return sb.toString()
    }
}
