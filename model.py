from dataclasses import dataclass
from typing import Optional


@dataclass
class StaInfo:
    lat: float
    lon: float
    idx: int
    mmi: Optional[int] = None
