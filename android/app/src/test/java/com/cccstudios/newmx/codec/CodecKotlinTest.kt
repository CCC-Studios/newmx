package com.cccstudios.newmx.codec

import org.junit.Assert.*
import org.junit.Test

/**
 * Codec unit tests. Use a synthetic minimal phrase-glyph map so tests
 * don't depend on the production v005-rev4 asset.
 *
 * Run with:  ./gradlew :app:testDebugUnitTest
 */
class CodecKotlinTest {

    /**
     * Minimal map covering one intent family, two structural patterns,
     * enough to exercise every code path in the encoder.
     */
    private val testMapJson = """
    {
      "meta": { "version": "test-v1" },
      "phrase_to_family_and_glyph": {
        "how to":      { "family": "HOW_TO_PROCEDURE", "glyph": "µ" },
        "in the":      { "family": "STRUCTURAL_BIGRAM", "glyph": "Ñ" },
        "of the":      { "family": "STRUCTURAL_BIGRAM", "glyph": "Ð" }
      }
    }
    """.trimIndent()

    private val codec: Codec = Codec.buildFromJsonString(testMapJson)

    // -----------------------------------------------------------------
    // Basic encoding
    // -----------------------------------------------------------------

    @Test
    fun `encodes a simple structural bigram`() {
        val out = codec.encode("walk in the park")
        // "in the" → Ñ, then cli5 strips space before glyph: "walkÑ park"
        // Note: structural pass uses \b so "walk in" doesn't get matched anywhere
        assertTrue(
            "Expected output to contain Ñ glyph, got: $out",
            out.contains("Ñ")
        )
        assertFalse(
            "Expected 'in the' to be replaced, got: $out",
            out.contains("in the")
        )
    }

    @Test
    fun `encodes a family-class phrase at line start`() {
        val out = codec.encode("how to use git rebase")
        assertTrue(
            "Expected µ glyph at start, got: $out",
            out.startsWith("µ")
        )
    }

    @Test
    fun `does not encode family phrase mid-sentence without boundary`() {
        // "how to" appears mid-sentence without a boundary trigger — should
        // NOT match (family pass is boundary-aware).
        val raw = "i know how to use git"
        val out = codec.encode(raw)
        // After normalization "i" stripped? Actually i is not a wrapper; should
        // survive. The match should NOT happen since there's no boundary.
        assertFalse(
            "Family phrase 'how to' should NOT match without boundary, got: $out",
            out.contains("µ")
        )
    }

    @Test
    fun `encodes family phrase after conjunction boundary`() {
        // "and how to" — the boundary lookbehind for "and" should trigger
        // family match here.
        val raw = "explain it and how to use it"
        val out = codec.encode(raw)
        assertTrue(
            "Expected µ glyph after 'and' boundary, got: $out",
            out.contains("µ")
        )
    }

    // -----------------------------------------------------------------
    // Empty / edge cases
    // -----------------------------------------------------------------

    @Test
    fun `empty input returns empty`() {
        assertEquals("", codec.encode(""))
    }

    @Test
    fun `whitespace-only input returns empty after normalization`() {
        // Normalizer trims, so pure whitespace becomes ""
        assertEquals("", codec.encode("   "))
    }

    @Test
    fun `text with no matches returns normalized text unchanged`() {
        val raw = "nothing matchable here xyz"
        val out = codec.encode(raw)
        assertEquals("nothing matchable here xyz", out)
    }

    // -----------------------------------------------------------------
    // Normalization
    // -----------------------------------------------------------------

    @Test
    fun `strips leading instruction wrapper`() {
        val out = codec.encode("can you how to install docker")
        // "can you " removed → "how to install docker" → µ install docker
        assertTrue(out.startsWith("µ"))
    }

    @Test
    fun `strips trailing politeness`() {
        val out = codec.encode("how to install docker thanks")
        // "thanks" stripped, "how to" → µ
        assertTrue(out.contains("µ"))
        assertFalse(out.contains("thanks"))
    }

    @Test
    fun `fixed-point wrapper stripping`() {
        // "please could you" — two layered wrappers
        val out = codec.encode("please could you how to install docker")
        assertTrue(out.startsWith("µ"))
        assertFalse(out.contains("please"))
        assertFalse(out.contains("could you"))
    }

    // -----------------------------------------------------------------
    // cli5 pre-glyph-space behavior
    // -----------------------------------------------------------------

    @Test
    fun `cli5 strips space before glyphs`() {
        val out = codec.encode("text and how to do thing")
        // After family match: "text and µ do thing"
        // cli5: "text andµ do thing"
        assertTrue(
            "Expected 'andµ' with no space, got: $out",
            out.contains("andµ") || !out.contains(" µ")
        )
    }

    // -----------------------------------------------------------------
    // Multi-line
    // -----------------------------------------------------------------

    @Test
    fun `multi-line encodes each line independently`() {
        val raw = "first line in the box\nhow to do it"
        val out = codec.encode(raw)
        assertTrue(out.contains("\n"))
        val lines = out.split("\n")
        assertEquals(2, lines.size)
        assertTrue("Line 1 should have Ñ: ${lines[0]}", lines[0].contains("Ñ"))
        assertTrue("Line 2 should have µ: ${lines[1]}", lines[1].contains("µ"))
    }

    @Test
    fun `code lines are not encoded`() {
        val raw = "    def add(a, b): return a + b"
        val out = codec.encode(raw)
        assertEquals(raw, out)
    }

    // -----------------------------------------------------------------
    // Codec API metadata
    // -----------------------------------------------------------------

    @Test
    fun `codec exposes version and mapping count`() {
        assertEquals("test-v1", codec.codecVersion)
        assertEquals(3, codec.numMappings)
    }

    @Test
    fun `decode table is buildable and contains family names`() {
        val table = codec.decodeTable
        assertTrue(table.contains("HOW_TO_PROCEDURE"))
        assertTrue(table.contains("µ"))
    }

    @Test
    fun `encodeWithTable includes decode table`() {
        val full = codec.encodeWithTable("how to install docker")
        assertTrue(full.contains("Decode table for this session"))
        assertTrue(full.contains("µ"))
    }

    // -----------------------------------------------------------------
    // Decode (lossy by design)
    // -----------------------------------------------------------------

    @Test
    fun `structural glyph round-trips exactly`() {
        val encoded = codec.encode("walk in the park")
        val decoded = codec.decode(encoded)
        // "in the" should reappear (structural is 1:1, but cli5 stripped the
        // leading space, so the decoded form may have "walkin the park")
        assertTrue(
            "Decoded should contain 'in the': $decoded",
            decoded.contains("in the")
        )
    }

    @Test
    fun `family glyph decodes to canonical phrase`() {
        val encoded = codec.encode("how to install docker")
        val decoded = codec.decode(encoded)
        // Only one phrase in HOW_TO_PROCEDURE family in test map, so canonical = "how to"
        assertTrue(decoded.contains("how to"))
    }

    // -----------------------------------------------------------------
    // Replacements diagnostic
    // -----------------------------------------------------------------

    @Test
    fun `replacements list includes the family that matched`() {
        val result = codec.encodeDetailed("how to install docker")
        assertEquals(1, result.replacements.size)
        assertEquals("HOW_TO_PROCEDURE", result.replacements[0].family)
        assertEquals("µ", result.replacements[0].glyph)
    }

    @Test
    fun `replacements list records every match`() {
        val result = codec.encodeDetailed("how to do the thing in the box")
        // Should record: 1 family (how to) + 1 structural (in the)
        assertTrue(result.replacements.size >= 2)
        val families = result.replacements.map { it.family }.toSet()
        assertTrue(families.contains("HOW_TO_PROCEDURE"))
        assertTrue(families.contains("STRUCTURAL_BIGRAM"))
    }
}
