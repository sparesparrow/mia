#!/usr/bin/env python3
import sys
import json
from datetime import datetime
import shutil
from pathlib import Path
from typing import Any, Dict

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape


def load_yaml(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"YAML parsing failed for {path}: {exc}") from exc


def build_variant(variant_name: str, i18n_file: str | None = None) -> None:
    """Render a single variant into dist/<variant_name>/ using Jinja2."""

    variant_key = i18n_file or variant_name.replace("-car", "")
    i18n_path = Path("web/i18n") / f"{variant_key}.yaml"
    if not i18n_path.exists():
        raise FileNotFoundError(f"Missing translation file: {i18n_path}")

    common_path = Path("web/i18n/common.yaml")
    build_data: Dict[str, Any] = {}

    if common_path.exists():
        build_data.update(load_yaml(common_path))

    build_data.update(load_yaml(i18n_path))

    output_dir = Path("dist") / variant_name
    output_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader("web/templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )

    template = env.get_template("index.html")
    base_path = f"/{variant_name}".rstrip("/")

    html_content = template.render(
        variant=variant_name,
        variant_key=variant_key,
        data=build_data,
        theme=variant_key,
        base_path=base_path,
        current_year=datetime.now().year,
    )

    (output_dir / "index.html").write_text(html_content, encoding="utf-8")

    css_source = Path("web/css") / f"{variant_key}.css"
    fallback_css = Path("web/css/default.css")

    if css_source.exists():
        shutil.copy2(css_source, output_dir / "style.css")
    elif fallback_css.exists():
        shutil.copy2(fallback_css, output_dir / "style.css")

    if fallback_css.exists():
        shutil.copy2(fallback_css, output_dir / "base.css")

    js_source = Path("web/js")
    if js_source.exists():
        shutil.copytree(js_source, output_dir / "js", dirs_exist_ok=True)

    assets_source = Path("web/assets")
    if assets_source.exists():
        shutil.copytree(assets_source, output_dir / "assets", dirs_exist_ok=True)

    print(json.dumps({"status": "ok", "variant": variant_name, "base_path": base_path}))


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/build_variant.py <variant_name> [i18n_file]")

    variant = sys.argv[1]
    i18n_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        build_variant(variant, i18n_file)
    except Exception as exc:  # pragma: no cover - surfaced to CI log
        print(f"❌ Failed to build variant '{variant}': {exc}")
        raise


if __name__ == "__main__":
    main()
