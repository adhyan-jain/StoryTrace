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


CHAPTER_PATTERN = re.compile(r'^\s*(?:Chapter\s+\d+|[IVXLCDM]+\.?)\s*$', re.IGNORECASE | re.MULTILINE)

class NovelParser:
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
                if CHAPTER_PATTERN.match(line):
                    # Save previous unit
                    if current_unit:
                        units.append(current_unit)
                        sequence += 1
                        
                    # Start new unit
                    current_unit = NarrativeUnit(
                        unit_id=f"{self.document_id}_chapter_{sequence}",
                        story_universe_id=self.story_universe_id,
                        document_id=self.document_id,
                        unit_type="chapter",
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
                    else:
                        # Sometimes text starts before a formal chapter heading (e.g. prologue)
                        current_unit = NarrativeUnit(
                            unit_id=f"{self.document_id}_prologue_0",
                            story_universe_id=self.story_universe_id,
                            document_id=self.document_id,
                            unit_type="passage",
                            sequence_number=sequence,
                            title="Prologue",
                            page_start=page_num + 1,
                            page_end=page_num + 1,
                            raw_text=line + "\n"
                        )
                        
        if current_unit:
            units.append(current_unit)
            
        return units
