import re


def clean_chapter_title_suffix(title_suffix: str) -> str:
    title = title_suffix.strip()
    title = re.sub(r"^\|\s*", "", title)
    title = re.sub(r"\s*\|\s*", " ", title)
    title = re.sub(r"\[\d{1,5}\]", "", title)
    title = re.sub(r"\s+\d{1,5}$", "", title)
    title = re.sub(r"(?:\s*\.\s*){3,}$", "", title)
    return re.sub(r"\s+", " ", title).strip(" .:-–")


def append_wrapped_chapter_title_line(text: str, match_end: int, title: str) -> str:
    following_text = text[match_end:].lstrip("\r\n")
    if not following_text:
        return title

    lines = [line.strip() for line in following_text.splitlines()[:5] if line.strip()]
    if not lines:
        return title

    continuation = clean_chapter_title_suffix(lines[0])
    if not continuation or len(continuation) <= 2 or is_chapter_title_stop_line(continuation):
        return title

    nearby_heading_text = " ".join(lines[1:5]).casefold()
    if ("learning" not in nearby_heading_text and "earning" not in nearby_heading_text) or (
        "objective" not in nearby_heading_text and "bjective" not in nearby_heading_text
    ):
        return title

    return f"{title} {continuation}".strip()


def is_chapter_title_stop_line(line: str) -> bool:
    return line.casefold() in {
        "learning objectives",
        "learning objective",
        "introduction",
        "references",
        "study questions and exercises",
    }


def has_dot_leader(text: str) -> bool:
    return bool(re.search(r"\s\.\s+\d{1,5}$", text.strip())) or (
        text.count(".") >= 3 and has_trailing_page_number(text)
    )


def has_trailing_page_number(text: str) -> bool:
    return bool(re.search(r"\s\d{1,5}$", text.strip()))


def chapter_label_for_title(label: str) -> str:
    return re.sub(r"\s+", " ", label).strip()

