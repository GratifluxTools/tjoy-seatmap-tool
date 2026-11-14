"""描画の中間表現（PNG/SVG の両方で使う）。TOHO版の scene と同じ考え方。"""
from dataclasses import dataclass, field


@dataclass
class Begin:
    id: str
    attrs: dict = field(default_factory=dict)
    title: str = ""


@dataclass
class End:
    pass


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float
    r: float = 0
    fill: str | None = None
    stroke: str | None = None
    sw: float = 0.7
    opacity: float | None = None  # 当たり判定用の透明矩形に使う


@dataclass
class Line:
    x1: float
    y1: float
    x2: float
    y2: float
    color: str
    w: float = 1.0


@dataclass
class Text:
    x: float
    y: float
    s: str
    size: float
    anchor: str = "middle"   # start / middle / end
    color: str = "#222222"
    bold: bool = False


@dataclass
class Scene:
    w: float
    h: float
    items: list = field(default_factory=list)
    bg: str = "#FFFFFF"


@dataclass
class ImageItem:
    x: float
    y: float
    w: float
    h: float
    data: bytes          # 元のファイルのバイト列（SVGの埋め込み用）
    mime: str
    img: object = None   # PIL.Image（PNG描画用）
