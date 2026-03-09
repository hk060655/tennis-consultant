import re
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class KnowledgeChunk:
    text: str
    source_file: str
    section_title: str
    skill_level: str
    chunk_id: str


SKILL_LEVEL_PATTERN = re.compile(r'适用水平[：:]\s*(.+?)(?:\s*$|\s*\n)', re.MULTILINE)


class KnowledgeLoader:
    def __init__(self, base_path: Path):
        self.base_path = base_path

    def load_all(self) -> list[KnowledgeChunk]:
        chunks = []
        for md_file in sorted(self.base_path.rglob("*.md")):
            if md_file.name == "README.md":
                continue
            chunks.extend(self._parse_file(md_file))
        return chunks

    def _parse_file(self, path: Path) -> list[KnowledgeChunk]:
        rel_path = str(path.relative_to(self.base_path))
        text = path.read_text(encoding="utf-8")
        return self._split_by_headings(text, rel_path)

    def _split_by_headings(self, text: str, source_file: str) -> list[KnowledgeChunk]:
        chunks = []
        # Split on level-2 headings
        parts = re.split(r'\n(?=## )', "\n" + text)
        for part in parts:
            part = part.strip()
            if not part or part.startswith('# '):
                continue
            if not part.startswith('## '):
                continue

            lines = part.split('\n')
            heading_line = lines[0].lstrip('#').strip()
            skill_level = self._extract_skill_level(heading_line) or "all"
            section_title = re.sub(r'[—\-–].*', '', heading_line).strip()
            body = '\n'.join(lines[1:]).strip()

            # Split body on ### headings
            sub_parts = re.split(r'\n(?=### )', body)
            pending = ""
            for i, sub in enumerate(sub_parts):
                combined = (pending + "\n" + sub).strip() if pending else sub.strip()
                if not combined:
                    continue
                if len(combined) < 300 and i < len(sub_parts) - 1:
                    pending = combined
                    continue
                if len(combined) > 600:
                    hard_chunks = self._hard_split(combined, 500)
                    for hc in hard_chunks:
                        if hc.strip():
                            chunks.append(self._make_chunk(
                                hc, source_file, section_title, skill_level, len(chunks)
                            ))
                else:
                    chunks.append(self._make_chunk(
                        combined, source_file, section_title, skill_level, len(chunks)
                    ))
                pending = ""
            if pending.strip():
                chunks.append(self._make_chunk(
                    pending, source_file, section_title, skill_level, len(chunks)
                ))
        return chunks

    def _hard_split(self, text: str, max_chars: int) -> list[str]:
        result = []
        while len(text) > max_chars:
            idx = text.rfind('\n', 0, max_chars)
            if idx == -1:
                idx = max_chars
            result.append(text[:idx].strip())
            text = text[idx:].strip()
        if text:
            result.append(text)
        return result

    def _extract_skill_level(self, heading: str) -> Optional[str]:
        m = SKILL_LEVEL_PATTERN.search(heading)
        return m.group(1).strip() if m else None

    def _make_chunk(
        self, text: str, source_file: str, section_title: str,
        skill_level: str, idx: int
    ) -> KnowledgeChunk:
        uid = hashlib.sha256(
            f"{source_file}:{section_title}:{idx}".encode()
        ).hexdigest()[:16]
        return KnowledgeChunk(
            text=text,
            source_file=source_file,
            section_title=section_title,
            skill_level=skill_level,
            chunk_id=uid,
        )
