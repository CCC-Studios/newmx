package com.cccstudios.newmx.codec

import java.util.regex.Pattern

/**
 * Phase 1 of the codec pipeline.
 *
 * Mirror of Python newmx/_normalize.py. Strips low-information surface
 * features before encoding:
 *   - Emojis
 *   - Politeness fillers ("please", "thanks", etc.)
 *   - AI-addressing greetings ("hey claude", "hi gpt", etc.)
 *   - Leading instruction wrappers ("can you", "i need you to", etc.)
 *   - Trailing courtesy phrases ("thanks in advance")
 *
 * Wrapper-stripping iterates to a fixed point (someone might write
 * "could you please" → strip "please" → strip "could you").
 *
 * Also includes code-line detection (skip encoding for code lines).
 */
object Normalizer {

    // -----------------------------------------------------------------------
    // Patterns
    // -----------------------------------------------------------------------

    // Emojis & pictographs.
    // We avoid \\p{So}/\\p{Cn} and surrogate-pair ranges (not valid in Android
    // regex character classes). Instead, do emoji stripping in Kotlin code
    // using Character.UnicodeBlock and the Unicode supplementary code points
    // for emoji blocks. See removeEmojis() below.
    //
    // Two simple BMP ranges still work fine in a regex char class:
    //   - Misc symbols & dingbats (U+2600 - U+27BF)
    //   - Variation Selector-16 (U+FE0F)
    private val EMOJI_BMP_PATTERN: Pattern = Pattern.compile(
        "[\\u2600-\\u27BF\\uFE0F]+"
    )

    /**
     * Strip emoji code points from a string.
     *
     * Handles surrogate pairs correctly by iterating code points instead of
     * char units. Removes:
     *   - BMP misc-symbols / dingbats range (via regex)
     *   - Supplementary emoji planes U+1F000 - U+1FFFF (via code point scan)
     */
    private fun removeEmojis(input: String): String {
        // First pass: BMP range via regex
        val pass1 = EMOJI_BMP_PATTERN.matcher(input).replaceAll("")

        // Second pass: walk code points, drop anything in supplementary emoji planes
        val sb = StringBuilder(pass1.length)
        var i = 0
        while (i < pass1.length) {
            val cp = pass1.codePointAt(i)
            // Emoji & pictograph supplementary planes:
            //   0x1F000 - 0x1FFFF covers most pictograph blocks
            //   0x2300 - 0x23FF  technical (BMP — already handled by regex above, but range overlaps)
            //   0xE0000 - 0xE007F tag chars
            val isEmoji = (cp in 0x1F000..0x1FFFF) || (cp in 0xE0000..0xE007F)
            if (!isEmoji) {
                sb.appendCodePoint(cp)
            }
            i += Character.charCount(cp)
        }
        return sb.toString()
    }

    // Trailing politeness (end of line)
    private val POLITENESS_TRAILING: Pattern = Pattern.compile(
        "[\\s,.!]*(?:please|pls|plz|thanks?|thank you|thanks in advance|" +
            "ty|tyvm|cheers|kindly|much appreciated|appreciate it)" +
            "[\\s,.!]*$",
        Pattern.CASE_INSENSITIVE
    )

    // Mid-sentence politeness — strips "please", "pls", "plz", "kindly"
    // anywhere they appear surrounded by whitespace. Leaves surrounding
    // text intact (collapses to single space).
    private val POLITENESS_MIDSENTENCE: Pattern = Pattern.compile(
        "(\\s)(?:please|pls|plz|kindly)(\\s)",
        Pattern.CASE_INSENSITIVE
    )

    // Leading politeness/AI-greeting (start of line)
    private val POLITENESS_LEADING: Pattern = Pattern.compile(
        "^(?:please|pls|plz|kindly|" +
            "hi|hello|hey|hi there|hello there|hey there|" +
            "hi claude|hello claude|hey claude|" +
            "hi gpt|hello gpt|hey gpt|hi chatgpt|hello chatgpt|hey chatgpt|" +
            "hi gemini|hello gemini|hey gemini|" +
            "hi assistant|hello assistant|hey assistant)" +
            "[\\s,.!]+",
        Pattern.CASE_INSENSITIVE
    )

    // Instruction wrappers (line start). Order longer-first to avoid premature
    // partial matches.
    private val INSTRUCTION_WRAPPER: Pattern = Pattern.compile(
        "^(?:" +
            // Longer wrappers first
            "i would like you to|" +
            "do you think you could|" +
            "is it possible to|" +
            "i need help with|" +
            "your task is to|" +
            "i want you to|" +
            "i need you to|" +
            "could you please|" +
            "would you please|" +
            "i would like to|" +
            "i want to know|" +
            "i would like|" +
            "could you|" +
            "would you|" +
            "can you|" +
            "help me|" +
            "i want to|" +
            "i need to" +
            ")\\s+",
        Pattern.CASE_INSENSITIVE
    )

    // Trailing courtesy
    private val TRAILING_COURTESY: Pattern = Pattern.compile(
        "\\s*(?:" +
            "thanks in advance|thank you in advance|" +
            "thanks so much|thank you so much|" +
            "much appreciated|appreciate it" +
            ")[\\s,.!]*$",
        Pattern.CASE_INSENSITIVE
    )

    // Code-line heuristic — these lines are skipped during encoding entirely.
    // Conservative: only obvious code markers, not just "looks codey".
    private val CODE_LINE_PATTERNS: List<Pattern> = listOf(
        Pattern.compile("^\\s*```"),                                 // markdown fence
        Pattern.compile("^\\s*(?:def|class|function|import|from|" +
            "const|let|var|public|private|return)\\s"),              // common code keywords
        Pattern.compile("^\\s*#include\\b"),                         // C-family include
        Pattern.compile("^\\s*//"),                                  // line comment
        Pattern.compile("^\\s*/\\*"),                                // block comment
        Pattern.compile("^\\s{4,}\\S"),                              // indented code block
        Pattern.compile("^\\s*[\\w_]+\\s*=\\s*[\\w_\\(\\[\\{].*[\\)\\]\\};]\\s*$"), // assignment
    )

    // -----------------------------------------------------------------------
    // Public API
    // -----------------------------------------------------------------------

    /**
     * Returns true if `line` looks like a line of code that should bypass
     * encoding entirely.
     */
    fun isCodeLine(line: String): Boolean {
        if (line.isBlank()) return false
        for (p in CODE_LINE_PATTERNS) {
            if (p.matcher(line).find()) return true
        }
        return false
    }

    /**
     * Normalize one line. Idempotent: calling normalizeLine() on already-
     * normalized text returns the same text.
     *
     * Fixed-point iteration on wrapper stripping — keeps removing leading
     * wrappers until none remain.
     */
    fun normalizeLine(input: String): String {
        if (input.isEmpty()) return input

        var text = input

// Strip emojis (one pass — no fixed point needed)
        text = removeEmojis(text)

        // Strip trailing courtesy (one pass)
        text = TRAILING_COURTESY.matcher(text).replaceAll("")

// Strip mid-sentence politeness FIRST (one pass). Doing this before
        // wrapper stripping helps the family pass see proper boundaries.
        text = POLITENESS_MIDSENTENCE.matcher(text).replaceAll(" ")

        // Strip leading and trailing politeness — fixed point because layered
        // wrappers can shadow each other ("please could you" → "could you").
        for (i in 0 until 8) {
            val before = text
            text = POLITENESS_LEADING.matcher(text).replaceFirst("")
            text = INSTRUCTION_WRAPPER.matcher(text).replaceFirst("")
            text = POLITENESS_TRAILING.matcher(text).replaceFirst("")
            // Re-run mid-sentence in case wrapper stripping exposed another instance
            text = POLITENESS_MIDSENTENCE.matcher(text).replaceAll(" ")
            if (text == before) break
        }

        return text.trim()
    }
}
