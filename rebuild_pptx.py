#!/usr/bin/env python3
"""Rebuild PPTX from extracted XML directory."""

import zipfile
from pathlib import Path

def rebuild_pptx(extracted_dir: Path, output_pptx: Path) -> None:
    """Rebuild PPTX by zipping the extracted directory."""
    # Remove old PPTX if it exists
    if output_pptx.exists():
        output_pptx.unlink()
    
    # Create new PPTX zip file
    with zipfile.ZipFile(output_pptx, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in sorted(extracted_dir.rglob('*')):
            if file_path.is_file():
                arcname = file_path.relative_to(extracted_dir)
                zipf.write(file_path, arcname=str(arcname))
    
    print(f"✓ Rebuilt {output_pptx.name}")

if __name__ == '__main__':
    extracted_root = Path(r"d:\FYP\Project\_pptx_extracted")
    pptx_path = Path(r"d:\FYP\Project\SafeVision_FYP_Defense (16).pptx")
    
    rebuild_pptx(extracted_root, pptx_path)
    print(f"✓ File saved: {pptx_path}")
