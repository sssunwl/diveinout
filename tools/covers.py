"""Deterministic brand artwork, standard library only; no remote assets."""
import hashlib
import html
import math
import random
import re
import struct
import zlib

COLORS = {'spot': '#14b8a6', 'beginner': '#38bdf8', 'gear': '#64748b',
          'safety': '#ff5470', 'ocean': '#22c55e', 'course': '#a78bfa', 'life': '#fbbf24'}
NO_START = '，。、：；！？）」』…'
NO_END = '（「『'

# Original category line art, drawn around (0, 0) in a 300px square.
ICONS = {
    'spot': 'M-80-65 Q0-120 80-65 Q120 0 80 65 Q0 120-80 65 Q-120 0-80-65Z M-50-45 0-72 50-45 65 12 30 60-30 60-65 12Z M0-72V-10 M-65 12 0-10 65 12 M0-10V55 M-83-50Q-155-115-135-35L-100-5 M83-50Q155-115 135-35L100-5 M-80 55Q-135 115-100 115L-55 88 M80 55Q135 115 100 115L55 88 M-20-98Q-35-150 0-148Q35-150 20-98 M-10 98 0 130 10 98',
    'beginner': 'M-125-65Q0-100 125-65L140 35Q125 95 55 90L15 40H-15L-55 90Q-125 95-140 35Z M-110-40-95 45Q-75 65-48 50L-20 15V-45Z M110-40 95 45Q75 65 48 50L20 15V-45Z M-135-30H-150V30H-140 M135-30H150V30H140 M115-70V-125H150V-90',
    'gear': 'M-60-95Q-60-120 0-120Q60-120 60-95V105Q60 140 0 140Q-60 140-60 105Z M-60-70H60 M-60 90H60 M-20-120V-145H20V-120 M0-145V-160H40 M60-70Q125-70 125 10V65 M-20-35H20 M-20-15H20',
    'safety': 'M0-145A145 145 0 1 1 0 145A145 145 0 1 1 0-145Z M0-70A70 70 0 1 0 0 70A70 70 0 1 0 0-70Z M-103-103-50-50 M103-103 50-50 M-103 103-50 50 M103 103 50 50 M-130-65-63-31 M130-65 63-31 M-130 65-63 31 M130 65 63 31',
    'ocean': 'M-10 140V35L-55-10V-90 M-55-10-110-45V-105 M-110-45-145-75 M-55-55-20-90V-130 M-10 65 55 5V-100 M55-30 110-65V-120 M110-65 145-95 M55-65 20-100V-145 M-10 105-90 65-125 15 M-90 65-135 80 M-10 120 90 80 120 25 M90 80 135 100 M-30 140H30',
    'course': 'M-140-95Q-140-115-120-115H120Q140-115 140-95V95Q140 115 120 115H-120Q-140 115-140 95Z M-140-65H140 M-105-90H-65 M-100-25H5 M-100 5H-10 M-100 35H-30 M65-35A40 40 0 1 1 65 45A40 40 0 1 1 65-35Z M45 40 35 85 65 70 95 85 85 40',
    'life': 'M-145 45H145L110 110H-105Z M-115 115Q-80 140-45 115Q-10 140 25 115Q60 140 95 115Q120 135 145 120 M-95 45V-20H55L100 45 M-55-20V-65H20V-20 M-40-65V-120 M-40-115 50-80H-40 M-70 0H-40V25H-70Z M-10 0H20V25H-10Z',
}


def cover_titles(title):
    """Separate the descriptive suffix without cutting the short name in a bracket."""
    match = re.search(r'[（(：:]', title)
    if not match or len(title[:match.start()].strip()) < 4:
        return title, ''
    short = title[:match.start()].strip()
    subtitle = title[match.end():].strip()
    if match.group() in '（(' and subtitle.endswith(('）', ')')):
        subtitle = subtitle[:-1].rstrip()
    if len(subtitle) > 26:
        subtitle = subtitle[:25].rstrip(NO_END) + '…'
    return short, subtitle


def title_lines(title):
    """Two lines, with Chinese opening/closing punctuation kept on its proper side."""
    if len(title) > 22:
        cut = 21
        while cut > 12 and title[cut-1].isascii() and title[cut-1].isalnum() and title[cut].isascii() and title[cut].isalnum():
            cut -= 1
        title = title[:cut].rstrip(NO_END + ' ') + '…'
    if len(title) <= 11:
        return [title]
    split = 11
    while split < len(title) and title[split] in NO_START:
        split += 1
    while split and title[split-1] in NO_END:
        split -= 1
    # Moving an opening mark can expose a preceding closing mark; keep both with
    # the first line, and start the next line after the complete punctuation run.
    if split < len(title) and title[split] in NO_START:
        while split < len(title) and title[split] in NO_START:
            split += 1
    # 不把英文單字拆成兩行(Dumague|te):退到單字開頭
    word_start = split
    while 0 < word_start < len(title) and title[word_start-1].isascii() and title[word_start-1].isalnum() \
            and title[word_start].isascii() and title[word_start].isalnum():
        word_start -= 1
    if word_start > 3:
        split = word_start
    return [line for line in (title[:split], title[split:]) if line]


def cover_svg(slug, title, category):
    rng = random.Random(int(hashlib.sha1(slug.encode()).hexdigest(), 16))
    color = COLORS[category]
    short, subtitle = cover_titles(title)
    lines = title_lines(short)
    # Even punctuation carried onto the first line stays inside x=64..624.
    font_size = min(56, 560 / max(len(line) for line in lines))
    shapes = []
    for i in range(6):
        x, y = rng.randint(900, 1200), rng.randint(160, 580)
        shapes.append(f'<ellipse cx="{x}" cy="{y}" rx="{180+i*38}" ry="{110+i*25}" transform="rotate(-24 {x} {y})" fill="none" stroke="{color}" stroke-opacity=".07"/>')
    for i in range(18):
        x, y, r = rng.randint(20, 1180), rng.randint(20, 610), rng.randint(2, 8)
        shapes.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="{color}" opacity=".12"/>')
    x, y = rng.randint(905, 935), rng.randint(325, 350)
    rotation, scale = rng.uniform(-8, 8), rng.uniform(.9, 1.1)
    icon = f'<g data-category-icon="{category}" transform="translate({x} {y}) rotate({rotation:.2f}) scale({scale:.3f})" fill="none" stroke="{color}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="{ICONS[category]}"/></g>'
    text = ''.join(f'<text class="cover-title" x="64" y="{300+i*78}" font-size="{font_size:.2f}" font-weight="700">{html.escape(line)}</text>' for i, line in enumerate(lines))
    sub = f'<text class="cover-subtitle" x="64" y="466" font-size="20" fill="#c5dce3">{html.escape(subtitle)}</text>' if subtitle else ''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-label="{html.escape(title, quote=True)}">
<defs><linearGradient id="sea" x1="1" y1="0" x2="0" y2="1"><stop stop-color="{color}" stop-opacity=".72"/><stop offset=".6" stop-color="{color}" stop-opacity=".18"/><stop offset="1" stop-color="#020a10"/></linearGradient><linearGradient id="beam" x2="0" y2="1"><stop stop-color="{color}" stop-opacity=".13"/><stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>
<rect width="1200" height="630" fill="#020a10"/><rect width="1200" height="630" fill="url(#sea)"/><path d="M760 0H930L650 630H180Z" fill="url(#beam)"/>{''.join(shapes)}{icon}
<g fill="#e9fbff" font-family="'PingFang TC','Noto Sans TC',sans-serif"><text x="64" y="90" font-size="30" font-weight="700">DiveInOut</text><text x="64" y="155" fill="{color}" font-family="monospace" font-size="18" letter-spacing="5">{category.upper()} / PAN-ASIA DIVE MAG</text>{text}{sub}<text x="64" y="565" font-size="17" fill="#8fb3bf">潛進亞洲的海。愈往下，看見愈深的世界。</text></g></svg>'''


def og_png():
    """1200x630 RGB PNG: original ocean gradient, beams and bubble rings."""
    width, height = 1200, 630
    raw = bytearray()
    bubbles = [(900, 280, 130), (1050, 430, 65), (790, 460, 22)]
    glyphs = {
        'D': ('11110','10001','10001','10001','10001','10001','11110'),
        'I': ('11111','00100','00100','00100','00100','00100','11111'),
        'V': ('10001','10001','10001','10001','10001','01010','00100'),
        'E': ('11111','10000','10000','11110','10000','10000','11111'),
        'N': ('10001','11001','11001','10101','10011','10011','10001'),
        'O': ('01110','10001','10001','10001','10001','10001','01110'),
        'U': ('10001','10001','10001','10001','10001','10001','01110'),
        'T': ('11111','00100','00100','00100','00100','00100','00100'),
    }
    pixels = {(position*6+col, row) for position, letter in enumerate('DIVEINOUT')
              for row, bits in enumerate(glyphs[letter]) for col, bit in enumerate(bits) if bit == '1'}
    for y in range(height):
        raw.append(0)
        for x in range(width):
            glow = max(0, 1 - math.hypot((x-850)/1000, (y-100)/750))
            r, g, b = int(2+9*glow), int(10+50*glow), int(16+58*glow)
            if any(abs(math.hypot(x-cx, y-cy)-radius) < 2 for cx, cy, radius in bubbles):
                r, g, b = 47, 180, 175
            # A simple original depth ruler, legible even in a small preview.
            if 105 <= x <= 109 and 145 <= y <= 485 or 105 <= x <= 165 and y in range(145, 486, 68):
                r, g, b = 47, 243, 224
            if (int((x-220)//11), int((y-270)//11)) in pixels and 220 <= x < 814 and 270 <= y < 347:
                r, g, b = (47, 243, 224) if 484 <= x < 616 else (233, 251, 255)
            raw.extend((r, g, b))
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind+data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b'')
