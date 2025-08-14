
from __future__ import annotations
import json, zipfile, shutil
from pathlib import Path
from typing import Dict, List, Optional
from ..core.models import SkillTree, Character

class Storage:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.data_dir = self.root / "data"
        self.trees_dir = self.data_dir / "trees"
        self.chars_dir = self.data_dir / "characters"
        self.trees_dir.mkdir(parents=True, exist_ok=True)
        self.chars_dir.mkdir(parents=True, exist_ok=True)

    def load_trees(self) -> Dict[str, SkillTree]:
        out = {}
        for p in sorted(self.trees_dir.glob("*.json")):
            try: out[SkillTree.from_dict(json.loads(p.read_text(encoding='utf-8'))).id] = SkillTree.from_dict(json.loads(p.read_text(encoding='utf-8')))
            except Exception as e: print("Failed to load", p, e)
        # fix: compute once
        trees = {}
        for p in sorted(self.trees_dir.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                t = SkillTree.from_dict(data); trees[t.id] = t
            except Exception as e:
                print("Failed to load", p, e)
        return trees

    def save_tree(self, t: SkillTree) -> None:
        (self.trees_dir / f"{t.id}.json").write_text(json.dumps(t.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def list_characters(self) -> List[str]:
        return sorted([p.stem for p in self.chars_dir.glob("*.json")])

    def load_character(self, name: str) -> Optional[Character]:
        p = self.chars_dir / f"{name}.json"
        if not p.exists(): return None
        return Character.from_dict(json.loads(p.read_text(encoding="utf-8")))

    def save_character(self, ch: Character) -> None:
        (self.chars_dir / f"{ch.name}.json").write_text(json.dumps(ch.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def set_character_image(self, ch: Character, src: Path) -> str:
        ext = src.suffix.lower() or ".png"
        dest_name = f"{ch.name}_image{ext}"
        dest = self.chars_dir / dest_name
        shutil.copy2(src, dest)
        ch.image = dest_name; self.save_character(ch)
        return dest_name

    def character_image_path(self, ch: Character):
        if not ch.image: return None
        p = self.chars_dir / ch.image
        return p if p.exists() else None

    def export_character_zip(self, name: str, out_zip: Path) -> bool:
        ch = self.load_character(name)
        if not ch: return False
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{ch.name}.json", json.dumps(ch.to_dict(), indent=2, ensure_ascii=False))
            if ch.image:
                img = self.chars_dir / ch.image
                if img.exists(): z.write(img, ch.image)
        return True

    def import_character(self, path: Path) -> Optional[str]:
        p = Path(path)
        if p.suffix.lower()==".zip":
            with zipfile.ZipFile(p, "r") as z:
                j = next((n for n in z.namelist() if n.lower().endswith(".json")), None)
                if not j: return None
                data = json.loads(z.read(j).decode("utf-8"))
                ch = Character.from_dict(data)
                if ch.image and ch.image in z.namelist(): z.extract(ch.image, self.chars_dir)
                self.save_character(ch); return ch.name
        else:
            data = json.loads(p.read_text(encoding="utf-8")); ch = Character.from_dict(data); self.save_character(ch); return ch.name
