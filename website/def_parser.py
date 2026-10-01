import re
from pathlib import Path
from typing import Dict, Any, List, Optional

def parse_def_file(def_path: Path, max_components: int = 3000) -> Dict[str, Any]:
    path = Path(def_path)
    if not path.exists() or not path.is_file():
        return {"error": f"DEF file non-existent: {def_path}"}

    diearea = [0, 0, 1000, 1000]
    units_distance = 1000
    components = []
    pins = []

    try:
        with open(path, "r", errors="ignore") as f:
            in_components = False
            in_pins = False
            
            for line in f:
                line_str = line.strip()
                if not line_str or line_str.startswith("#"):
                    continue

                if line_str.startswith("UNITS DISTANCE MICRONS"):
                    parts = line_str.split()
                    if len(parts) >= 4:
                        try: units_distance = float(parts[3])
                        except ValueError: pass

                elif line_str.startswith("DIEAREA"):
                    # DIEAREA ( 0 0 ) ( 343647 344511 ) ;
                    matches = re.findall(r'\(\s*(-?\d+)\s+(-?\d+)\s*\)', line_str)
                    if len(matches) >= 2:
                        try:
                            x1, y1 = float(matches[0][0]), float(matches[0][1])
                            x2, y2 = float(matches[1][0]), float(matches[1][1])
                            diearea = [x1 / units_distance, y1 / units_distance, x2 / units_distance, y2 / units_distance]
                        except ValueError: pass

                elif line_str.startswith("COMPONENTS"):
                    in_components = True
                    continue
                elif line_str.startswith("END COMPONENTS"):
                    in_components = False
                    continue

                elif line_str.startswith("PINS"):
                    in_pins = True
                    continue
                elif line_str.startswith("END PINS"):
                    in_pins = False
                    continue

                if in_components and line_str.startswith("-"):
                    if len(components) < max_components:
                        # - PHY_EDGE_ROW_0_Left_1267 TAPCELL_ASAP7_75t_R + FIXED ( 648 1080 ) N ;
                        parts = line_str.split()
                        if len(parts) >= 3:
                            comp_name = parts[1]
                            macro_name = parts[2]
                            coord_match = re.search(r'\(\s*(-?\d+)\s+(-?\d+)\s*\)', line_str)
                            if coord_match:
                                cx = float(coord_match.group(1)) / units_distance
                                cy = float(coord_match.group(2)) / units_distance
                                components.append({
                                    "name": comp_name,
                                    "macro": macro_name,
                                    "x": round(cx, 2),
                                    "y": round(cy, 2)
                                })

                elif in_pins and line_str.startswith("-"):
                    # - clk + NET clk + DIRECTION INPUT + PLACED ( 0 172255 ) N ;
                    parts = line_str.split()
                    if len(parts) >= 2:
                        pin_name = parts[1]
                        coord_match = re.search(r'\(\s*(-?\d+)\s+(-?\d+)\s*\)', line_str)
                        if coord_match:
                            px = float(coord_match.group(1)) / units_distance
                            py = float(coord_match.group(2)) / units_distance
                            pins.append({
                                "name": pin_name,
                                "x": round(px, 2),
                                "y": round(py, 2)
                            })
    except Exception as e:
        return {"error": f"Failed to parse DEF file: {e}"}

    return {
        "diearea": diearea,
        "units": units_distance,
        "total_components": len(components),
        "components": components,
        "pins": pins
    }
