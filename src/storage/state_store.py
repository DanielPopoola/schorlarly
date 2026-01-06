from pathlib import Path
from dataclasses import asdict
import json
from enum import Enum
from dacite import from_dict, Config

from src.models import GlobalState
from .helpers import EnumEncoder


class StateStore:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.state_file = storage_path / "state.json"

    def save(self, state: GlobalState) -> None:
        self.storage_path.mkdir(parents=True, exist_ok=True)

        state_dict = asdict(state)

        with open(self.state_file, "w") as f:
            json.dump(state_dict, f, cls=EnumEncoder, indent=2)

    def load(self) -> GlobalState | None:
        if not self.exists():
            return None

        with open(self.state_file, "r") as f:
            data = json.load(f)

        config = Config(cast=[Enum])

        return from_dict(data_class=GlobalState, data=data, config=config)

    def exists(self) -> bool:
        return self.state_file.exists()

    def delete(self) -> None:
        if self.exists():
            self.state_file.unlink()
