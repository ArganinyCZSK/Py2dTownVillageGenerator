# Py2D Town & Village Generator

A 2D map generator for villages and towns, written in plain Python with **no external libraries**.
Generate a settlement layout with one click, edit it with the mouse, turn a picture of a real map into an editable map, and export it to PNG, SVG, JSON and more.

Created by **ArganinyCZSK / Jan Hepp** · [Discord](https://discord.gg/gn85hyddQC)

---

## Features

### Map generation
- Generates 2D maps of **villages** or **towns**: houses, churches and town halls, roads, dirt tracks, street lamps, walls, fences, fields, forests and ponds.
- Towns have **defensive walls with towers and gates** and a central market square. Villages have a village green with a small pond.
- Every map gets a random name and a **seed**. The same seed always generates the same map again.

### Settings (left panel)
- Map and settlement size, number of main roads and streets, building density and size.
- Turn town walls, street lamps, the square / village green and churches on or off.
- Amount of fields, fenced pastures, forests, single trees, yard fences and brick walls.
- Look of the map: grass texture, shadows, lamp light, title, legend and scale bar. These apply instantly.

### Map editing
- **Drag and drop** houses, trees, lamps, fields, ponds, walls and fences.
- **Rotate** with the mouse wheel or the `Q` / `E` keys.
- **Delete** with the `Delete` key or a right click.
- **Add** houses, street lamps, trees, wooden fences, brick walls and stone walls (drag to draw a wall).
- **Undo** with `Ctrl+Z`.

### Map image import
- Turns a **PNG or JPG picture of a real map** into a fully editable map.
- Detects buildings, roads, highways, dirt tracks, ponds and streams, forests, gardens and fields.
- Works with **historical topographic maps** (e.g. 1950s-1980s scans) and **modern maps** with a white background. The map style is detected automatically and can also be chosen by hand.

### Export
Files are saved into the same folder as the program.

| Format | Type | Notes |
|---|---|---|
| PNG, BMP, PPM | Image | Export scale 1x-4x |
| SVG, EPS | Vector | Print quality, any size |
| JSON | Map file | Can be opened again and edited (`Open map`) |
| ALL | All of the above | Saves every format at once |

---

## Requirements

- **Windows, Linux or macOS**
- **Python 2.6 or newer, or any Python 3**. No `pip install` needed, everything is built in.
- **Tkinter** for the window (included in the standard Python installer). Without Tkinter the program still generates and saves PNG maps.

---

## How to run

**Windows:** double-click `run_map_generator.bat`.
The launcher finds Python on your computer by itself (Python 3 first, then Python 2.6+) and shows which version it uses.

**Any system:**
```
python map_generator.py
```

### Command line (no window)
```
python map_generator.py --type town --export png,svg,json
python map_generator.py --type village --seed 42 --export all --scale 2
python map_generator.py --count 5 --export png
python map_generator.py --import my_map.png --export png,json
python map_generator.py --import my_map.png --style modern --export png
```

| Option | Meaning |
|---|---|
| `--type` | `village`, `town` or `random` |
| `--seed` | Seed number (same seed = same map) |
| `--export` | Formats separated by commas: `png,bmp,ppm,svg,eps,json` or `all` |
| `--scale` | Image export scale 1-4 |
| `--count` | How many maps to generate |
| `--width`, `--height` | Map size in pixels |
| `--import` | Build the map from a PNG/JPG map picture |
| `--style` | Import map style: `auto`, `old` or `modern` |

---

## Controls

| Action | Control |
|---|---|
| New map | `F5` or the buttons at the top |
| Move object | Drag with the left mouse button |
| Rotate object | Mouse wheel, `Q` / `E` |
| Delete object | `Delete` or right click |
| Undo | `Ctrl+Z` |
| Export | `Ctrl+S` |
| Deselect | `Esc` |

## License

**CC BY (Creative Commons Attribution)**. You may share and adapt this program, but you must give credit to the author: **ArganinyCZSK / Jan Hepp**.

## Community

Questions, ideas and maps you made: **[Discord](https://discord.gg/gn85hyddQC)**
