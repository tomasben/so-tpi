import csv
import random
from dataclasses import dataclass

APP_NAMES: list[str] = [
    "Firefox",
    "PDF Arranger",
    "GIMP",
    "Inkscape",
    "Papers",
    "Safari",
    "Xcode",
    "Notion",
    "Google Chrome",
    "Microsoft Word",
    "Microsoft Excel",
    "Microsoft Powerpoint",
    "Microsoft OneNote",
    "Visual Studio Code",
    "Whatsapp Desktop",
    "Spotify",
    "Canva",
    "Draw.io",
    "GeoGebra",
    "Trello",
    "Discord",
    "Zoom",
    "Ghostty",
    "VirtualBox",
    "Docker Desktop",
    "GitHub Desktop",
    "Git Bash",
]
APP_NAMES_ITER = iter(random.sample(APP_NAMES, len(APP_NAMES)))


@dataclass(frozen=True)
class ProcessSpec:
    pid: int
    size: int
    arrival_time: int
    burst_time: int
    name: str = next(APP_NAMES_ITER)


def read_specs(path: str) -> list[ProcessSpec]:
    with open(path, newline="", encoding="utf-8") as file:
        return [
            ProcessSpec(
                pid=int(row["id"]),
                size=int(row["size"]),
                arrival_time=int(row["arrival_time"]),
                burst_time=int(row["burst_time"]),
            )
            for row in csv.DictReader(file)
        ]
