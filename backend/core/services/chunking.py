import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Chunk:
    index: int
    text: str
    section: str = ""
    page: int | None = None

def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\r\n", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()

def chunk_text(text: str, target_words: int = 220, overlap_words: int = 35) -> list[Chunk]:
    clean = normalize_text(text)
    if not clean:
        return []
    paragraphs = re.split(r"\n(?=(?:\d+(?:\.\d+)*\s|SCOPE|Scope|REFERENCES|National Foreword))", clean)
    chunks, buffer, section = [], [], ""
    for paragraph in paragraphs:
        heading = re.match(r"^((?:\d+(?:\.\d+)*)?\s*(?:SCOPE|Scope|REFERENCES|References|NATIONAL FOREWORD)[^\n]*)", paragraph)
        if heading:
            section = heading.group(1)[:300]
        words = paragraph.split()
        if buffer and len(buffer) + len(words) > target_words:
            chunks.append(Chunk(len(chunks), " ".join(buffer), section))
            buffer = buffer[-overlap_words:]
        buffer.extend(words)
    if buffer:
        chunks.append(Chunk(len(chunks), " ".join(buffer), section))
    return chunks

