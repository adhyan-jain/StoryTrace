import argparse
from .parser import ScreenplayParser

def main():
    parser = argparse.ArgumentParser(description="Parse screenplay PDF into scenes")
    parser.add_argument("pdf_path", help="Path to the screenplay PDF")
    parser.add_argument("--id", default="demo_script", help="Screenplay ID")
    args = parser.parse_args()

    screenplay_parser = ScreenplayParser(args.id)
    scenes = screenplay_parser.parse(args.pdf_path)

    for scene in scenes:
        print(f"Scene {scene.number}")
        if scene.page_start == scene.page_end:
            print(f"Page {scene.page_start}")
        else:
            print(f"Page {scene.page_start}-{scene.page_end}")
        print(scene.heading)
        print()
    
    print(f"Total scenes parsed: {len(scenes)}")

if __name__ == "__main__":
    main()
