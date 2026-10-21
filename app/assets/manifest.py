from dataclasses import dataclass, field, asdict
from pathlib import Path
import json


@dataclass
class ClipManifest:
    """一个动作（Clip）的元数据，导入后写入 clip.json。"""
    action: str
    source_file: str
    src_fps: float
    src_frames: int
    duration: float
    out_size: tuple[int, int]
    out_fps: int
    frame_count: int
    anchor: tuple[float, float] = (0.5, 1.0)
    loop: bool = True
    frames: list[str] = field(default_factory=list)

    def to_json(self, path: Path):
        data = asdict(self)
        data["out_size"] = list(self.out_size)
        data["anchor"] = list(self.anchor)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def from_json(cls, path: Path) -> "ClipManifest":
        data = json.loads(path.read_text(encoding="utf-8"))
        data["out_size"] = tuple(data["out_size"])
        data["anchor"] = tuple(data["anchor"])
        return cls(**data)