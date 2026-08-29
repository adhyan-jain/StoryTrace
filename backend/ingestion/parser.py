import pymupdf
import re
from typing import List, Optional
from .models import Scene

# Regex for common screenplay scene headings
HEADING_PATTERN = re.compile(
    r'^\s*(?:[0-9]+\s*)?(INT\.|EXT\.|INT\./EXT\.|I/E\.|INT/EXT\.|INT/EXT|INT|EXT)\s*(.*?)(?:\s*[-–—]\s*(DAY|NIGHT|CONTINUOUS|MORNING|EVENING|AFTERNOON|LATER|MOMENTS LATER|DUSK|DAWN))?\s*$',
    re.IGNORECASE | re.MULTILINE
)

class ScreenplayParser:
    def __init__(self, screenplay_id: str):
        self.screenplay_id = screenplay_id

    def extract_text_with_pages(self, pdf_path: str) -> List[tuple[int, str]]:
        doc = pymupdf.open(pdf_path)
        pages = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            # 1-indexed pages
            pages.append((page_num + 1, text))
        return pages

    def parse_scenes(self, pages: List[tuple[int, str]]) -> List[Scene]:
        scenes = []
        current_scene_text = []
        current_heading = None
        current_scene_number = 1
        current_scene_start_page = 1
        
        # We need to process line by line to keep track of pages properly
        for page_num, page_text in pages:
            lines = page_text.split('\n')
            for line in lines:
                # Basic cleanup
                line_stripped = line.strip()
                if not line_stripped:
                    current_scene_text.append(line)
                    continue

                # Check if this line is a heading
                match = HEADING_PATTERN.match(line)
                
                # Exclude obvious false positives (too long or mostly lowercase)
                if match and len(line_stripped) < 120 and line_stripped.upper() == line_stripped:
                    # Save the previous scene
                    if current_heading is not None:
                        scene = self._build_scene(
                            current_scene_number,
                            current_heading,
                            "\n".join(current_scene_text),
                            current_scene_start_page,
                            page_num
                        )
                        scenes.append(scene)
                        current_scene_number += 1

                    # Start a new scene
                    current_heading = line
                    current_scene_text = [line]
                    current_scene_start_page = page_num
                else:
                    if current_heading is not None:
                        current_scene_text.append(line)

        # Add the last scene
        if current_heading is not None:
            scene = self._build_scene(
                current_scene_number,
                current_heading,
                "\n".join(current_scene_text),
                current_scene_start_page,
                pages[-1][0] if pages else current_scene_start_page
            )
            scenes.append(scene)

        return scenes

    def _build_scene(self, number: int, heading: str, text: str, page_start: int, page_end: int) -> Scene:
        heading_clean = heading.strip()
        match = HEADING_PATTERN.match(heading_clean)
        
        interior_ext = None
        location = None
        time_of_day = None
        
        if match:
            interior_ext = match.group(1).strip() if match.group(1) else None
            location = match.group(2).strip() if match.group(2) else None
            time_of_day = match.group(3).strip() if match.group(3) else None

        scene_id = f"{self.screenplay_id}_scene_{number}"
        
        return Scene(
            scene_id=scene_id,
            screenplay_id=self.screenplay_id,
            number=number,
            heading=heading_clean,
            interior_ext=interior_ext,
            location=location,
            time_of_day=time_of_day,
            raw_text=text.strip(),
            page_start=page_start,
            page_end=page_end
        )

    def parse(self, pdf_path: str) -> List[Scene]:
        pages = self.extract_text_with_pages(pdf_path)
        return self.parse_scenes(pages)
