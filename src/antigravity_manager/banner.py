from rich.console import Console
from rich.text import Text
import math
import random
import shutil

console = Console()

def lerp(a, b, t):
    return a + (b - a) * t

def blend(c1, c2, t):
    t = t ** 1.47
    t = 0.82 * t + 0.08 * math.sin(3.2 * t)
    r = int(lerp(c1[0], c2[0], t))
    g = int(lerp(c1[1], c2[1], t))
    b = int(lerp(c1[2], c2[2], t))
    return f"#{r:02x}{g:02x}{b:02x}"

def print_logo():
    logo = r"""
    _   _  _ _____ ___ ____ ____     _ __     _____ _______   __
   / \ | \| |_   _|_ _/ ___|  _ \   / \ \ \   / /_ _|_   _\ \ / /
  / _ \|  . ` | | |  | | |  _| |_) | / _ \ \ \ / / | |  | |  \ V / 
 / ___ \ |\  | | |  | | |___|  _ < / ___ \ \ V /  | |  | |   | |  
/_/   \_\_| \_| |_| |___\____|_| \_\/_/   \_\_/  |___| |_|   |_|  
      M  A  N  A  G  E  R
""".strip().split("\n")

    palette = [
        (0x2E, 0x7B, 0xEA),
        (0x6C, 0x5B, 0xD8),
        (0xB6, 0x6D, 0xB9),
        (0xE8, 0x8A, 0xA6),
        (0xFF, 0xB6, 0xC1),
    ]

    H = len(logo)
    for i, line in enumerate(logo):
        tline = Text()
        W = len(line)
        for j, ch in enumerate(line):
            raw = (i * 0.72 + j * 0.44)
            t = raw / (H * 0.72 + W * 0.44)
            seg = t * (len(palette) - 1)
            idx = int(seg)
            t2 = seg - idx
            c1 = palette[idx]
            c2 = palette[min(idx + 1, len(palette) - 1)]
            tline.append(ch, style=blend(c1, c2, t2))
        console.print(tline)

    console.print("[dim]🌌 Powerful CLI interface for managing Antigravity accounts and backups.[/dim]\n")
