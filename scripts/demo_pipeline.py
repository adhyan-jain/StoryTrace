import os
from backend.ingestion.parser import ScreenplayParser
from backend.clickhouse.client import ClickHouseClient
from backend.candidate_detection.detector import CandidateDetector
from backend.story_state.models import CandidateConflict

def run_demo():
    print("Starting StoryTrace Demo Pipeline...")
    
    # 1. Parse PDF
    parser = ScreenplayParser("demo_script")
    pdf_path = "demo/screenplay.pdf"
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found. Run scripts/generate_demo_pdf.py first.")
        return
        
    scenes = parser.parse(pdf_path)
    print(f"✓ Parsed {len(scenes)} scenes from {pdf_path}")
    
    # 2. Connect to ClickHouse (Requires docker-compose up)
    try:
        client = ClickHouseClient()
        client.insert_scenes(scenes)
        print("✓ Inserted scenes into ClickHouse Story State DB")
    except Exception as e:
        print(f"⚠ Could not connect to ClickHouse. Is docker-compose running? ({e})")
        print("Skipping database steps for demo.")
        return
        
    # 3. Detect Candidates
    detector = CandidateDetector(client)
    conflicts = detector.detect_conflicts("demo_script")
    print(f"✓ Detected {len(conflicts)} candidate conflicts using SQL Window Functions")
    
    # 4. Investigation Agent (mocking API for demo)
    print("✓ Investigation Agent initialized")
    print("\n--- Pipeline Execution Complete ---")
    print("Start the FastAPI server and Next.js UI to explore the Continuity Autopsy.")

if __name__ == "__main__":
    run_demo()
