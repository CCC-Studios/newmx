package com.cccstudios.newmx.codec

/**
 * Mirror of Python newmx/_constants.py.
 *
 * These three constants must match the Python codec exactly. If you upgrade
 * the codec (e.g. v005-rev5), update these lists to match.
 *
 * To verify parity:
 *   1. python -c "import newmx; print(newmx._constants.INTENT_FAMILIES)"
 *   2. Compare with the set below.
 */
object CodecConstants {

    /**
     * The 38 intent families (v005-rev4).
     *
     * These names are matched against each map entry's "family" field to
     * decide whether the entry is part of the family layer (boundary-aware)
     * or the structural layer (verbatim substitution).
     */
    val INTENT_FAMILIES: Set<String> = setOf(
        "ANALYZE_EVALUATE",
        "BRAINSTORM_IDEATE",
        "BUILD_PROJECT",
        "CALCULATE_COMPUTE",
        "CLASSIFY_CATEGORIZE",
        "CODE_DEBUG",
        "CODE_WRITE",
        "COMPARE_DIFFERENCE",
        "CONDITIONAL_HYPOTHETICAL",
        "CONFIRM_VERIFY",
        "CONTINUE_APPROVAL",
        "CONTINUE_COMPLETE",
        "CORRECT_FIX",
        "DEFINE_CONCEPT",
        "EMAIL_COMPOSE",
        "EXPLAIN_REASON",
        "EXTRACT_FROM_TEXT",
        "FOLLOW_INSTRUCTION",
        "FORMAT_OUTPUT",
        "GENERATE_LIST",
        "GENERATE_TEXT",
        "HOW_TO_PROCEDURE",
        "IMAGE_GENERATION",
        "OPINION_SUBJECTIVE",
        "PLAN_STRATEGIZE",
        "QUANTIFY_MEASURE",
        "RECOMMEND_SUGGEST",
        "REPORT_BACK",
        "REWRITE_TRANSFORM",
        "ROLEPLAY_ACT_AS",
        "SELECTION_CHOOSE",
        "SENTIMENT_TONE",
        "SUMMARIZE_CONDENSE",
        "TEACH_TUTOR",
        "TEMPORAL_WHEN",
        "TRANSLATE_LANG",
        "USER_PROVIDED_CONTENT",
        "WEB_SEARCH"
    )

    /**
     * Conjunctions that act as family-pass boundary markers (rev3).
     * Order matters: longer ones first so regex alternation prefers them.
     */
    val FAMILY_BOUNDARY_CONJUNCTIONS: List<String> = listOf(
        "then", "plus", "and", "but", "or", "so"
    )

    /**
     * Phrases banned from family matching (compile-time filter).
     *
     * Stub for now. If your Python BANNED_FAMILY_PHRASES contains entries,
     * port them verbatim here as lowercase strings. The map is loaded
     * normally, but these phrases will be skipped during compilation.
     */
    val BANNED_FAMILY_PHRASES: Set<String> = emptySet()
}
