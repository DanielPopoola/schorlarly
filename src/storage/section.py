import json
from pathlib import Path
from dataclasses import asdict
from dacite import from_dict

from src.models import Section
from src.storage.helpers import EnumEncoder


class SectionStore:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.sections_dir = storage_path / "sections"
        self.sections_dir.mkdir(parents=True, exist_ok=True)

    def save_section(self, section: Section) -> None:
        file_path = self.sections_dir / f"section_{section.section_id:03d}.json"

        with open(file_path, "w") as f:
            json.dump(asdict(section), f, cls=EnumEncoder, indent=2)

    def get_section(self, section_id: int) -> Section | None:
        file_path = self.sections_dir / f"section_{section_id:03d}.json"

        if not file_path.exists():
            return None

        with open(file_path, "r") as f:
            data = json.load(f)
            return from_dict(data_class=Section, data=data)

    def list_sections(self) -> list[Section]:
        sections = []
        for file_path in sorted(self.sections_dir.glob("section_*.json")):
            with open(file_path, "r") as f:
                data = json.load(f)
                sections.append(from_dict(data_class=Section, data=data))
        return sections
