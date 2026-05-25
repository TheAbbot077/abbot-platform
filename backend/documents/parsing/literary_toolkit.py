import re

from documents.models import ContentClassification

from .types import DetectedConcept


LITERARY_MARKER = "[Literary Toolkit]"


LITERARY_TERMS = {
    "plot",
    "setting",
    "character",
    "theme",
    "conflict",
    "symbolism",
    "imagery",
    "metaphor",
    "simile",
    "personification",
    "irony",
    "tone",
    "mood",
    "diction",
    "narrative voice",
    "point of view",
    "foreshadowing",
    "flashback",
    "allegory",
    "motif",
    "dialogue",
    "characterization",
    "genre",
    "author's purpose",
    "author’s purpose",
    "poem",
    "novel",
    "play",
    "short story",
    "literature",
}


LITERARY_CLASSIFICATIONS = {
    ContentClassification.NOVEL,
    ContentClassification.PLAY,
    ContentClassification.POEM,
    ContentClassification.SHORT_STORY,
    ContentClassification.LITERATURE_TEXTBOOK,
}


def classify_document_content(title: str, document_text: str) -> str:
    """Classify broad document type for extraction without exposing personal data."""

    text = f"{title}\n{document_text[:20_000]}".casefold()
    term_hits = sum(1 for term in LITERARY_TERMS if term in text)

    if re.search(r"\b(poems|poetry|stanza|sonnet|verse)\b", text):
        return ContentClassification.POEM
    if re.search(r"\b(act\s+[ivx\d]+|scene\s+[ivx\d]+|stage directions?|dramatis personae|soliloquy)\b", text):
        return ContentClassification.PLAY
    if re.search(r"\b(short stories|short story)\b", text):
        return ContentClassification.SHORT_STORY
    if term_hits >= 5 and re.search(r"\b(literary devices|literary terms|language arts|analysis|metaphor|simile)\b", text):
        return ContentClassification.LITERATURE_TEXTBOOK
    if re.search(r"\b(novel|chapter\s+1)\b", text) and _looks_narrative(document_text):
        return ContentClassification.NOVEL
    if term_hits >= 3 and _looks_narrative(document_text):
        return ContentClassification.SHORT_STORY
    if re.search(r"\b(learning objectives|chapter objectives|key terms|review questions|textbook)\b", text):
        return ContentClassification.TEXTBOOK
    return ContentClassification.UNKNOWN


def is_literary_classification(content_classification: str) -> bool:
    return content_classification in LITERARY_CLASSIFICATIONS


def is_literary_material(chapter_title: str, chapter_text: str, content_classification: str = "") -> bool:
    """Return true when a chapter should be taught through literary analysis."""

    if is_literary_classification(content_classification):
        return True

    text = f"{chapter_title}\n{chapter_text[:6000]}".casefold()
    term_hits = sum(1 for term in LITERARY_TERMS if term in text)

    if term_hits >= 3:
        return True

    if re.search(r"\b(act|scene|canto|stanza|poem|novel|short story|literature)\b", text):
        return True

    # Plays often have repeated speaker labels. This is deliberately
    # conservative so normal textbooks are not forced into literary mode.
    speaker_labels = re.findall(r"(?m)^[A-Z][A-Z .'-]{2,30}:\s+\S+", chapter_text)
    if len(speaker_labels) >= 4:
        return True

    dialogue_lines = re.findall(r"['\"“‘][^'\"”’]{10,}['\"”’]", chapter_text)
    narrative_verbs = re.findall(r"\b(said|asked|replied|cried|whispered|answered)\b", chapter_text, flags=re.IGNORECASE)
    return len(dialogue_lines) >= 5 and len(narrative_verbs) >= 3


def detect_literary_learning_units(
    chapter_title: str,
    chapter_text: str,
    content_classification: str = "",
) -> list[DetectedConcept]:
    """Create ordered literary analysis units for the current unlocked section.

    Literature does not always expose textbook-style concept headings. These
    units let students move through what happens, then how the author creates
    meaning, while preserving the same sequential unlock model.
    """

    mode = _literary_mode(chapter_title, chapter_text, content_classification)
    metadata = build_literary_section_metadata(chapter_title, 1, chapter_text, content_classification)
    units = {
        "poetry": [
            ("Speaker and situation", "Identify who speaks, what is happening, and the poem's immediate situation."),
            ("Imagery and diction", "Analyze the poem's images and word choices."),
            ("Figurative language", "Study metaphors, similes, personification, symbolism, and other devices."),
            ("Tone and mood", "Explain the attitude and feeling created by the poem."),
            ("Theme and interpretation", "Connect the poem's details to its larger meaning."),
            ("Structure and form", "Notice how stanza, rhythm, repetition, or organization shape meaning."),
        ],
        "play": [
            ("Scene summary", "Explain what happens in this scene or act."),
            ("Conflict and stakes", "Identify the main conflict and why it matters."),
            ("Dialogue and characterization", "Analyze how speech reveals character and relationships."),
            ("Dramatic techniques", "Study irony, stage action, structure, or dramatic tension."),
            ("Themes and symbols", "Connect repeated ideas or objects to meaning."),
            ("Important quotations", "Interpret key lines from the scene without using later spoilers."),
        ],
        "literature_textbook": [
            ("Literary terms in this section", "Learn the literary terms introduced in this section."),
            ("How the examples work", "Use the provided examples to see how each device creates meaning."),
            ("Interpretation practice", "Practice explaining evidence from the text in your own words."),
        ],
        "narrative": [
            ("Chapter summary", "Explain what happens in this section of the text."),
            ("Key events", "Track the important events in order without using later spoilers."),
            ("Character development", "Analyze how characters change, choose, speak, or reveal motives."),
            ("Conflict and tension", "Identify the central struggle in this section and why it matters."),
            ("Themes and ideas", "Connect events and character choices to larger ideas."),
            ("Symbols and literary devices", "Study imagery, symbolism, irony, foreshadowing, diction, or motif."),
            ("Important quotations", "Interpret important lines or passages from this unlocked section."),
            ("Interpretation questions", "Practice explaining what the text means and how the author creates that meaning."),
        ],
    }[mode]

    return [
        DetectedConcept(title=title, summary=f"{LITERARY_MARKER} {summary} {_metadata_summary_for_unit(title, metadata)}".strip())
        for title, summary in units
        if _unit_has_support(title, chapter_text, mode)
    ]


def build_literary_section_metadata(
    section_title: str,
    section_sequence: int,
    section_text: str,
    content_classification: str,
) -> dict:
    """Store literature-aware extraction fields as chapter metadata."""

    return {
        "section_title": section_title,
        "section_sequence": section_sequence,
        "content_classification": content_classification or ContentClassification.UNKNOWN,
        "summary": _summary(section_text),
        "key_events": _sentences_matching(section_text, [r"\b(arrives?|leaves?|discovers?|decides?|meets?|finds?|returns?|waits?|goes?)\b"], limit=5),
        "characters_present": _characters(section_text),
        "character_development": _sentences_matching(section_text, [r"\b(character|changes?|realizes?|learns?|chooses?|motive|feels?)\b"], limit=4),
        "themes": _term_sentences(section_text, ["theme", "justice", "love", "power", "identity", "freedom", "responsibility", "faith", "fear"]),
        "symbols": _term_sentences(section_text, ["symbol", "motif", "lantern", "road", "light", "dark", "shadow", "river", "door"]),
        "literary_devices": _detected_devices(section_text),
        "important_quotes": _quotes(section_text),
        "vocabulary": _vocabulary(section_text),
        "interpretation_questions": _interpretation_questions(content_classification),
    }


def is_literary_summary(summary: str) -> bool:
    return summary.strip().startswith(LITERARY_MARKER)


def _literary_mode(chapter_title: str, chapter_text: str, content_classification: str = "") -> str:
    if content_classification == ContentClassification.POEM:
        return "poetry"
    if content_classification == ContentClassification.PLAY:
        return "play"
    if content_classification == ContentClassification.LITERATURE_TEXTBOOK:
        return "literature_textbook"
    text = f"{chapter_title}\n{chapter_text[:6000]}".casefold()
    if re.search(r"\b(poem|stanza|line break|rhyme|speaker|sonnet|verse)\b", text):
        return "poetry"
    if re.search(r"\b(act|scene|stage direction|monologue|soliloquy)\b", text):
        return "play"
    if sum(1 for term in LITERARY_TERMS if term in text) >= 3 and re.search(r"\b(define|example|device|analysis)\b", text):
        return "literature_textbook"
    return "narrative"


def _looks_narrative(text: str) -> bool:
    return bool(
        re.search(r"['\"â€œâ€˜][^'\"â€â€™]{10,}['\"â€â€™]", text)
        or re.search(r"\b(said|asked|replied|walked|looked|thought|felt)\b", text, flags=re.IGNORECASE)
    )


def _metadata_summary_for_unit(title: str, metadata: dict) -> str:
    if title in {"Chapter summary", "Scene summary", "Speaker and situation"} and metadata["summary"]:
        return f"Focus: {metadata['summary']}"
    if title in {"Key events"} and metadata["key_events"]:
        return f"Key events: {'; '.join(metadata['key_events'][:3])}"
    if title in {"Character development", "Dialogue and characterization"} and metadata["characters_present"]:
        return f"Characters present: {', '.join(metadata['characters_present'][:6])}"
    if title in {"Themes and ideas", "Themes and symbols", "Theme and interpretation"} and metadata["themes"]:
        return f"Themes: {'; '.join(metadata['themes'][:3])}"
    if title in {"Symbols and literary devices", "Figurative language"} and metadata["literary_devices"]:
        return f"Devices: {', '.join(metadata['literary_devices'][:8])}"
    if title == "Important quotations" and metadata["important_quotes"]:
        return f"Quotes: {' | '.join(metadata['important_quotes'][:2])}"
    return ""


def _summary(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    return " ".join(sentences[:2])[:700]


def _sentences_matching(text: str, patterns: list[str], limit: int = 5) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
    matches = []
    for sentence in sentences:
        if any(re.search(pattern, sentence, flags=re.IGNORECASE) for pattern in patterns):
            matches.append(sentence[:300])
        if len(matches) >= limit:
            break
    return matches


def _term_sentences(text: str, terms: list[str], limit: int = 5) -> list[str]:
    return _sentences_matching(text, [rf"\b{re.escape(term)}\b" for term in terms], limit=limit)


def _characters(text: str) -> list[str]:
    names = re.findall(r"\b[A-Z][a-z]{2,}\b", text)
    ignored = {"Chapter", "The", "This", "That", "When", "Then", "There", "Their", "Literary"}
    unique = []
    for name in names:
        if name in ignored or name in unique:
            continue
        unique.append(name)
        if len(unique) >= 12:
            break
    return unique


def _detected_devices(text: str) -> list[str]:
    normalized = text.casefold()
    devices = [
        "symbolism",
        "imagery",
        "metaphor",
        "simile",
        "personification",
        "irony",
        "tone",
        "mood",
        "diction",
        "foreshadowing",
        "flashback",
        "allegory",
        "motif",
        "dialogue",
        "point of view",
    ]
    return [device for device in devices if device in normalized]


def _quotes(text: str) -> list[str]:
    return [quote[:300] for quote in re.findall(r"['\"â€œâ€˜]([^'\"â€â€™]{10,})['\"â€â€™]", text)[:8]]


def _vocabulary(text: str) -> list[str]:
    words = re.findall(r"\b[A-Za-z][A-Za-z'-]{8,}\b", text)
    common = {"character", "chapter", "literary", "important", "questions", "interpretation"}
    unique = []
    for word in words:
        normalized = word.casefold()
        if normalized in common or normalized in unique:
            continue
        unique.append(normalized)
        if len(unique) >= 12:
            break
    return unique


def _interpretation_questions(content_classification: str) -> list[str]:
    if content_classification == ContentClassification.POEM:
        return [
            "Who is speaking, and what situation does the poem present?",
            "How do imagery and diction shape the poem's tone?",
            "What theme is suggested by the poem's details?",
        ]
    if content_classification == ContentClassification.PLAY:
        return [
            "What conflict drives this scene?",
            "How does dialogue reveal character or tension?",
            "What dramatic technique shapes the audience's understanding?",
        ]
    return [
        "What happens in this section, and why does it matter?",
        "How does the author reveal character, conflict, or theme?",
        "Which detail or quotation best supports your interpretation?",
    ]


def _unit_has_support(title: str, chapter_text: str, mode: str) -> bool:
    normalized = chapter_text.casefold()
    if title in {"Character development", "Dialogue and characterization"}:
        return bool(re.search(r"\b(character|said|asked|replied|he|she|they|protagonist|antagonist)\b", normalized))
    if title in {"Symbols and literary devices", "Themes and symbols", "Figurative language", "Literary terms in this section"}:
        return bool(any(term in normalized for term in LITERARY_TERMS)) or mode in {"poetry", "literature_textbook"}
    if title == "Important quotations":
        return bool(re.search(r"['\"“‘][^'\"”’]{10,}['\"”’]", chapter_text))
    return True
