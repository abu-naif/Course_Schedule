"""Regenerate the course-book shortcut assets with the project's Pillow dependency."""
from pathlib import Path
from PIL import Image, ImageDraw

out = Path(__file__).resolve().parents[1] / 'static' / 'icons'
out.mkdir(parents=True, exist_ok=True)
size = 1024
im = Image.new('RGB', (size, size), '#2563eb')
d = ImageDraw.Draw(im)
# Two open pages and a center spine read as a course book at small sizes.
left = [(205, 300), (330, 280), (512, 332), (512, 770), (330, 718), (205, 740)]
right = [(512, 332), (694, 280), (819, 300), (819, 740), (694, 718), (512, 770)]
d.polygon(left, fill='#ffffff')
d.polygon(right, fill='#dbeafe')
d.line([(512, 340), (512, 758)], fill='#2563eb', width=24)
for y in (420, 515, 610):
    d.line([(268, y), (443, y + 30)], fill='#93c5fd', width=24)
for y in (420, 515, 610):
    d.line([(581, y + 30), (756, y)], fill='#60a5fa', width=24)
# A bookmark makes the book feel like a student's course material.
d.polygon([(677, 285), (730, 287), (730, 405), (703, 385), (677, 405)], fill='#1d4ed8')
for n in (32, 180, 192, 512):
    im.resize((n, n), Image.Resampling.LANCZOS).save(out / f'icon-{n}.png')
im.save(out / 'favicon.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64)])
(out / 'icon.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"><rect width="1024" height="1024" rx="180" fill="#2563eb"/><path d="M205 300l125-20 182 52v438l-182-52-125 22z" fill="white"/><path d="M512 332l182-52 125 20v440l-125-22-182 52z" fill="#dbeafe"/><path d="M512 340v418" stroke="#2563eb" stroke-width="24"/><path d="M268 420l175 30m-175 65l175 30m-175 65l175 30" stroke="#93c5fd" stroke-width="24"/><path d="M581 450l175-30m-175 125l175-30m-175 125l175-30" stroke="#60a5fa" stroke-width="24"/><path d="M677 285l53 2v118l-27-20-26 20z" fill="#1d4ed8"/></svg>''')
