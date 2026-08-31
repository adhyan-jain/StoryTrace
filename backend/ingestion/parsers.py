import fitz
import re
from typing import List
from backend.ingestion.models import NarrativeUnit
import uuid

HEADING_PATTERN = re.compile(r'^\s*(?:INT\.|EXT\.|INT/EXT\.|I/E\.)\s+.*$', re.MULTILINE)

class ScreenplayParser:
    def __init__(self, document_id: str, story_universe_id: str = "default_universe"):
        self.document_id = document_id
        self.story_universe_id = story_universe_id

    def parse(self, pdf_path: str) -> List[NarrativeUnit]:
        doc = fitz.open(pdf_path)
        units = []
        current_unit = None
        sequence = 1
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            
            lines = text.split('\n')
            for line in lines:
                if HEADING_PATTERN.match(line):
                    # Save previous unit
                    if current_unit:
                        units.append(current_unit)
                        sequence += 1
                        
                    # Start new unit
                    current_unit = NarrativeUnit(
                        unit_id=f"{self.document_id}_scene_{sequence}",
                        story_universe_id=self.story_universe_id,
                        document_id=self.document_id,
                        unit_type="scene",
                        sequence_number=sequence,
                        title=line.strip(),
                        page_start=page_num + 1,
                        page_end=page_num + 1,
                        raw_text=line + "\n"
                    )
                else:
                    if current_unit:
                        current_unit.raw_text += line + "\n"
                        current_unit.page_end = page_num + 1
                        
        if current_unit:
            units.append(current_unit)
            
        return units


CHAPTER_PATTERN = re.compile(r'^\s*Chapter\s+\d+\b', re.IGNORECASE)

class NovelParser:
    def __init__(self, document_id: str, story_universe_id: str = "default_universe"):
        self.document_id = document_id
        self.story_universe_id = story_universe_id

    def parse(self, pdf_path: str) -> List[NarrativeUnit]:
        doc = fitz.open(pdf_path)
        units = []
        current_unit = None
        current_unit_lines = []
        sequence = 1
        last_chapter_page = -1
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            
            lines = text.split('\n')
            for line in lines:
                line_stripped = line.strip()
                # Skip TOC bullets
                if line_stripped.startswith('•'):
                    continue
                    
                is_chapter_heading = bool(CHAPTER_PATTERN.match(line_stripped))
                
                if is_chapter_heading:
                    # Drop repeat headings on the same page (e.g. a differently
                    # formatted duplicate heading right after the real one) so
                    # they don't get echoed into the chapter body as text.
                    if page_num == last_chapter_page:
                        continue
                    last_chapter_page = page_num

                    # Save previous unit
                    if current_unit:
                        current_unit.raw_text = "".join(current_unit_lines)
                        units.append(current_unit)
                        sequence += 1
                        
                    # Start new unit
                    current_unit = NarrativeUnit(
                        unit_id=f"{self.document_id}_chapter_{sequence}",
                        story_universe_id=self.story_universe_id,
                        document_id=self.document_id,
                        unit_type="chapter",
                        sequence_number=sequence,
                        title=line_stripped,
                        page_start=page_num + 1,
                        page_end=page_num + 1,
                        raw_text=""
                    )
                    current_unit_lines = [line + "\n"]
                else:
                    if current_unit:
                        current_unit_lines.append(line + "\n")
                        current_unit.page_end = page_num + 1
                    else:
                        # Prologue/Front matter
                        current_unit = NarrativeUnit(
                            unit_id=f"{self.document_id}_prologue_0",
                            story_universe_id=self.story_universe_id,
                            document_id=self.document_id,
                            unit_type="passage",
                            sequence_number=sequence,
                            title="Prologue & Front Matter",
                            page_start=page_num + 1,
                            page_end=page_num + 1,
                            raw_text=""
                        )
                        current_unit_lines = [line + "\n"]
                        
        if current_unit:
            current_unit.raw_text = "".join(current_unit_lines)
            units.append(current_unit)

        return units


# Lines-per-page approximation for plain-text screenplay formats (Fountain)
# that carry no real page boundaries of their own -- standard screenplay
# formatting convention, used only to give NarrativeUnit.page_start/page_end
# a meaningful (if approximate) value rather than always 1.
_FOUNTAIN_LINES_PER_PAGE = 55


class FountainParser:
    """Fountain (.fountain) is plain text, not a fitz-openable container
    format like PDF/EPUB, so this reads the file directly rather than
    reusing ScreenplayParser's page-based fitz loop -- same heading pattern
    and NarrativeUnit shape, different source."""

    def __init__(self, document_id: str, story_universe_id: str = "default_universe"):
        self.document_id = document_id
        self.story_universe_id = story_universe_id

    def parse(self, fountain_path: str) -> List[NarrativeUnit]:
        with open(fountain_path, encoding="utf-8") as f:
            lines = f.readlines()

        units: List[NarrativeUnit] = []
        current_unit: NarrativeUnit | None = None
        sequence = 1

        for line_num, line in enumerate(lines):
            page = (line_num // _FOUNTAIN_LINES_PER_PAGE) + 1
            if HEADING_PATTERN.match(line):
                if current_unit:
                    units.append(current_unit)
                    sequence += 1

                current_unit = NarrativeUnit(
                    unit_id=f"{self.document_id}_scene_{sequence}",
                    story_universe_id=self.story_universe_id,
                    document_id=self.document_id,
                    unit_type="scene",
                    sequence_number=sequence,
                    title=line.strip(),
                    page_start=page,
                    page_end=page,
                    raw_text=line,
                )
            elif current_unit:
                current_unit.raw_text += line
                current_unit.page_end = page

        if current_unit:
            units.append(current_unit)

        return units
