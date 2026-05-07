"""
NewMx Path 1 — internal constants.

Normalization rules, intent families, banlist, emoji-strip pattern.
Lifted from path1_pipeline_b3_v005_rev4_FAST_cli5.py and frozen at v005-rev4.
"""

import re

# Politeness regex — self-consumes trailing punctuation (rev1 fix)
POLITENESS_PATTERNS = [
    r"\bplease[,;:]?\s*", r"\bpls[,;:]?\s*", r"\bplz[,;:]?\s*",
    r"\bthank you[,;:]?\s*",
    r"\bthanks[,;:]?\s*",
    r"\bthx[,;:]?\s*",
    r"\bty[,;:]?\s*",
    r"\bkindly[,;:]?\s*",
    r"\bif you don't mind[,;:]?\s*",
    r"\bif you would[,;:]?\s*",
    r"\bif possible[,;:]?\s*",
]

# Emoji strip — Unicode-block character class, stable across Unicode revisions
# because new emojis fall WITHIN existing blocks, not new ones.
EMOJI_PATTERN = re.compile(
    "["
    "\U000000A9-\U000000AE"  # © ®
    "\U0000203C-\U00002049"  # general punctuation symbols (‼ ⁉)
    "\U00002122-\U00002139"  # letterlike symbols (™ ℹ)
    "\U00002194-\U000021AA"  # arrows
    "\U0000231A-\U0000231B"  # watch, hourglass
    "\U000023E9-\U000023FA"  # media controls
    "\U000024C2"             # circled M
    "\U000025AA-\U000025FE"  # geometric shapes
    "\U00002600-\U000027BF"  # misc symbols + dingbats
    "\U00002934-\U00002935"  # arrows
    "\U00002B05-\U00002B55"  # arrows + shapes
    "\U00003030"             # 〰
    "\U0000303D"             # 〽
    "\U00003297-\U00003299"  # ㊗ ㊙
    "\U0001F000-\U0001F02F"  # mahjong
    "\U0001F0A0-\U0001F0FF"  # playing cards
    "\U0001F100-\U0001F64F"  # enclosed alphanumerics + transport + emoticons
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F700-\U0001F77F"  # alchemical
    "\U0001F780-\U0001F7FF"  # geometric extended
    "\U0001F800-\U0001F8FF"  # supplemental arrows-C
    "\U0001F900-\U0001F9FF"  # supplemental symbols & pictographs
    "\U0001FA00-\U0001FA6F"  # chess
    "\U0001FA70-\U0001FAFF"  # symbols & pictographs extended-A
    "\U0001F1E6-\U0001F1FF"  # regional indicators (flags)
    "\u200D"                 # ZWJ
    "\uFE0F"                 # variation selector-16
    "\U0001F3FB-\U0001F3FF"  # skin tone modifiers
    "]"
)

LEADING_WRAPPERS = [
    "i need you to","i want you to","i would like you to","i would love for you to",
    "i am asking you to","i am going to ask you to",
    "can you please","can you","could you please","could you",
    "would you please","would you",
    "are you capable of","are you able to","are able to",
    "your task is to","your job is to","your goal is to",
    "i need help with","i need to","help me to","help me",
    "is it possible to","is it possible for you to",
    "do you think you can","do you think you could",
    "i was wondering if you could","i was hoping you could",
    "quick question","a quick question","one quick question","one more question",
    "another question","mind if i ask","off topic but","sorry but","sorry to ask",
    "i'm sorry but","im sorry but","apologies but","ok so","okay so","alright so",
    "i'd like to","id like to","i'd like you to","id like you to",
    "i would appreciate it if","it would be great if","it would be helpful if",
    "it would help if","i was thinking","i was thinking that",
    "i've been thinking","ive been thinking","as you know","as i mentioned",
    "as we discussed","may i","need your help","need your help with",
    "need a hand with","give me a hand with","help me out","help me out with",
    "quick favor","can u","could u",
]

# AI addressing — extended in v005-rev4 with cordial greetings
AI_ADDRESSING = [
    "hey chatgpt","hey chat gpt","hey claude","hey gemini","hey ai",
    "hey opus","hey sonnet","hey haiku","hey gpt",
    "hello chatgpt","hello chat","hello claude",
    "hi chatgpt","hi claude","hi gemini",
    "dear ai","dear chat","ok chat",
    "hello there","hi there","hey there",
    "hello","hi","hey","hiya","howdy","yo","sup",
    "whats up","what's up",
    "good morning","good afternoon","good evening","good day",
    "how are you","how are you doing","how's it going","hows it going",
    "how have you been","hope you are well","hope you're well","hope youre well",
    "hope this finds you well",
    "greetings","salutations",
    "bonjour","hola","ciao","namaste","shalom",
]

# Trailing wrappers — extended in v005-rev3/rev4 with orphan beneficiary
# suffixes (for me / to me / with me) and cordial farewells (bye / goodbye / etc).
TRAILING_WRAPPERS = [
    "thanks in advance","thank you in advance","thanks so much","thank you so much",
    "i appreciate your help","i appreciate the help","appreciate the help",
    "sorry for the inconvenience","sorry to bother you","my apologies",
    "if that's okay","if thats okay","if that's ok","if thats ok",
    "if that works","if that makes sense","hope that makes sense",
    "hope this makes sense","does that make sense","when you get a chance",
    "when you have time","no rush","take your time",
    "for me","to me","with me",
    "goodbye","good bye","good night","good evening",
    "bye bye","bye",
    "see you","see ya","see you later","see you tomorrow","see you soon",
    "talk to you later","talk to you tomorrow","talk to you soon","speak soon",
    "catch you later","farewell","adios","au revoir","ciao",
    "have a good one","have a good day","have a good night","have a great day",
    "good job","great job","nice job",
]

# Code-line markers — if any of these appear, treat the line as code and skip
# all normalization + encoding (preserves code blocks intact).
CODE_SKIP_MARKERS = [
    "console.","def ","import ","from import",
    "public class","protected ","private ","void ",
    " => "," { "," } ","};",");"
]

# Banlist — phrases that must never become glyphs. Too generic; cause harmful
# compression in many contexts. Permanent across all revisions.
BANNED_FAMILY_PHRASES = frozenset([
    "to do","to make","need to","to get","to find","to create",
    "be able to","able to","want to","you are a",
    "why","draw","illustrate","imagine","error","explain",
])

# Intent families — 38 semantic-intent categories. Each maps to a single glyph
# at codec build time. Entries here are the ALL CAPS family identifiers.
INTENT_FAMILIES = frozenset([
    # v001 (12)
    "DEFINE_CONCEPT","HOW_TO_PROCEDURE","GENERATE_TEXT","GENERATE_LIST",
    "COMPARE_DIFFERENCE","ROLEPLAY_ACT_AS","EXPLAIN_REASON","CODE_WRITE",
    "CODE_DEBUG","IMAGE_GENERATION","REWRITE_TRANSFORM","FOLLOW_INSTRUCTION",
    # v002 (8)
    "SUMMARIZE_CONDENSE","TRANSLATE_LANG","ANALYZE_EVALUATE",
    "RECOMMEND_SUGGEST","EXTRACT_FROM_TEXT","CORRECT_FIX",
    "PLAN_STRATEGIZE","BRAINSTORM_IDEATE",
    # v004b (1)
    "BUILD_PROJECT",
    # v004c (8)
    "CONTINUE_COMPLETE","CONDITIONAL_HYPOTHETICAL","OPINION_SUBJECTIVE",
    "FORMAT_OUTPUT","CONFIRM_VERIFY","CLASSIFY_CATEGORIZE",
    "CALCULATE_COMPUTE","EMAIL_COMPOSE",
    # v004d (6)
    "QUANTIFY_MEASURE","TEMPORAL_WHEN","SELECTION_CHOOSE",
    "TEACH_TUTOR","SENTIMENT_TONE","USER_PROVIDED_CONTENT",
    # v005-rev2 (2)
    "WEB_SEARCH","REPORT_BACK",
    # v005-rev4 (1)
    "CONTINUE_APPROVAL",
])

# Conjunctions that act as family-boundary markers (rev3 fix). Coordinating
# only — subordinating conjunctions (because, while, although, etc.) are NOT
# boundary markers because they introduce dependent clauses where the second
# intent is subordinate to the first, not parallel.
FAMILY_BOUNDARY_CONJUNCTIONS = ("and", "or", "then", "plus", "but", "so")
