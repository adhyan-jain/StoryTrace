import pytest
from backend.ingestion.parser import ScreenplayParser

def test_heading_regex():
    import re
    from backend.ingestion.parser import HEADING_PATTERN
    
    assert HEADING_PATTERN.match("INT. WAREHOUSE - NIGHT")
    assert HEADING_PATTERN.match("EXT. STREET - DAY")
    assert HEADING_PATTERN.match("INT/EXT. CAR - CONTINUOUS")
    assert HEADING_PATTERN.match("I/E. CAR - CONTINUOUS")
    assert HEADING_PATTERN.match("INT WAREHOUSE")
    assert HEADING_PATTERN.match("  INT. WAREHOUSE - NIGHT  ")

def test_parse_scenes():
    parser = ScreenplayParser("test_script")
    pages = [
        (1, "INT. WAREHOUSE - NIGHT\n\nJohn walks in.\n\nHe looks around.\n\nEXT. STREET - DAY\n\nJohn walks out.\n\n"),
        (2, "He continues walking.\n\nINT/EXT. CAR - CONTINUOUS\n\nJohn drives away.")
    ]
    
    scenes = parser.parse_scenes(pages)
    
    assert len(scenes) == 3
    
    s1 = scenes[0]
    assert s1.number == 1
    assert s1.heading == "INT. WAREHOUSE - NIGHT"
    assert s1.interior_ext == "INT."
    assert s1.location == "WAREHOUSE"
    assert s1.time_of_day == "NIGHT"
    assert s1.page_start == 1
    assert s1.page_end == 1
    
    s2 = scenes[1]
    assert s2.number == 2
    assert s2.heading == "EXT. STREET - DAY"
    assert s2.interior_ext == "EXT."
    assert s2.location == "STREET"
    assert s2.time_of_day == "DAY"
    assert s2.page_start == 1
    assert s2.page_end == 2
    
    s3 = scenes[2]
    assert s3.number == 3
    assert s3.heading == "INT/EXT. CAR - CONTINUOUS"
    assert s3.interior_ext == "INT/EXT."
    assert s3.location == "CAR"
    assert s3.time_of_day == "CONTINUOUS"
    assert s3.page_start == 2
    assert s3.page_end == 2
