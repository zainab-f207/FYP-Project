#!/usr/bin/env python3
"""Update SafeVision presentation slides for the ML and OCR modules."""

from __future__ import annotations

from pathlib import Path
import sys
import zipfile

PPTX_PATH = Path(r"d:\FYP\Project\SafeVision_FYP_Defense (16).pptx")
EXTRACTED_ROOT = Path(r"d:\FYP\Project\_pptx_extracted")

REPLACEMENTS: dict[Path, list[tuple[str, str]]] = {
    EXTRACTED_ROOT / "ppt" / "slides" / "slide2.xml": [
        ("Random Forest + Poisson hybrid", "3 models work together"),
        ("5-engine voting pipeline", "3 active OCR engines + 4 fields"),
    ],
    EXTRACTED_ROOT / "ppt" / "slides" / "slide4.xml": [
        (
            "Two machine-learning models — Random Forest and Poisson — work side by side to score every area, every hour, on a 0–100 risk scale that is easy to read on the heatmap.",
            "Three models work together: Random Forest gives High/Medium/Low, Poisson gives the percentage chance, and a legacy fallback keeps the system working if the newer model ever fails.",
        ),
        (
            "A 5-engine OCR pipeline reads Punjab Police FIRs in Urdu and English, corrects place names with a 268-entry dictionary, and verifies the law sections cited using an AI language model.",
            "A 3-engine OCR pipeline reads Punjab Police FIRs in Urdu and English, extracts date, time, law sections, and area, and checks the law sections with an AI language model.",
        ),
        (
            "Web push notifications fire when a verified crime happens within 1.5 km of a user's home, work or current location — with a cooldown so the user is not spammed with repeated alerts.",
            "Web push notifications fire when a verified crime happens within 5 km of a user's home, work or current location — with three alert types and a cooldown so the user is not spammed with repeated alerts.",
        ),
        (
            "We generate three alternate paths between two points and rank them by both average risk and worst-point risk along the line. The user sees the safest, not just the fastest.",
            "We generate 3 to 5 route options between two points and rank them by both average risk and worst-point risk along the line. The user sees the safest, not just the fastest.",
        ),
    ],
    EXTRACTED_ROOT / "ppt" / "slides" / "slide15.xml": [
        (
            "How a verified crime becomes a risk score on the heatmap",
            "How three models turn a crime into a clear risk score",
        ),
        (
            "WHY A HYBRID, NOT A SINGLE MODEL?",
            "WHY THREE MODELS WORK BEST",
        ),
        (
            "is great at deciding if an area is High, Medium, or Low risk — but doesn't tell us 'how likely is the next hour'.",
            "looks at crime history and decides whether the case is High, Medium, or Low. It is fast and reliable, but it does not give a percentage chance for the next hour.",
        ),
        (
            "answers exactly that — 'what is the probability of a crime in the next hour?' — but is too smooth to draw clean category boundaries.",
            "gives the percentage chance for the next hour. It is excellent for timing, but by itself it does not give a crisp High, Medium, or Low label.",
        ),
        (
            "they give us crisp colour categories AND a real probability — both of which the UI uses.",
            "Model 3 is the legacy fallback. If the newer models cannot load, we still return a safe answer so the app never breaks.",
        ),
        (
            "Median /crimes/predict latency",
            "Median prediction latency",
        ),
    ],
    EXTRACTED_ROOT / "ppt" / "slides" / "slide21.xml": [
        (
            "THREE ROUTES SCORED",
            "3-5 ROUTES COMPARED",
        ),
        (
            "Plain English: OSRM (the routing engine) doesn't naturally give us truly different alternates — they tend to look like the same path with small wiggles. Our trick: we pick a midpoint between A and B, then push that midpoint sideways (perpendicular) by a few hundred metres. We force OSRM to route THROUGH each shifted midpoint. Result: three genuinely different paths we can actually compare.",
            "Plain English: OSRM often gives very similar alternates. Our trick is perpendicular via-points: we take the midpoint from A to B, shift it sideways with fixed offsets (about 0.015 and 0.030 degrees), and force OSRM through those points. Result: clearly different corridors we can compare for safety.",
        ),
        (
            "If is_night (10pm – 4am):  score × 0.85",
            "If is_night (8pm – 6am):  score × 0.85",
        ),
        (
            "70% on average risk rewards consistently safe corridors; 30% on the worst point on the route penalises any one nasty hotspot. After dark, every score drops 15% — pushing the 'safest' choice to differ from daytime.",
            "70% on average risk rewards consistently safer corridors; 30% on the worst point penalises one dangerous hotspot. At night (8pm-6am), scores get the night factor so the safest route can differ from daytime.",
        ),
    ],
    EXTRACTED_ROOT / "ppt" / "slides" / "slide22.xml": [
        (
            "OCR PIPELINE — 5 ENGINES VOTING",
            "OCR PIPELINE — 3 ACTIVE ENGINES + 4 FIELDS",
        ),
        (
            "12,517 lines of code reading handwritten Urdu FIRs",
            "12,517 lines of code turning FIR scans into usable data",
        ),
        (
            "Before OCR, we take an MD5 fingerprint of the upload. If we've seen the exact same file before, we skip OCR entirely and reuse the result — instant, 100% accurate, zero cost. Cache currently holds 975 known FIRs. Bit-exact match means zero false positives.",
            "Before OCR, we take an MD5 fingerprint of the upload. If we have seen the exact same file before, we skip OCR and reuse the old answer. That saves time and keeps re-uploads at zero cost. The cache holds 975 known FIRs. Bit-exact match means zero false positives.",
        ),
        (
            "Punjab Police FIRs follow a fixed layout. We scan Row 4 first (place of incident — most reliable), Row 2 second (complainant address with police thana), and Header last (FIR number, station, date). Skipping low-yield areas saves time and reduces false reads.",
            "Punjab Police FIRs follow a mostly fixed layout. We scan the most useful regions first, which makes OCR faster and reduces wrong reads.",
        ),
        (
            "OCR rarely returns a perfect string. We compare each OCR'd word with our dictionary using SequenceMatcher (a string-similarity score from 0 to 1). If similarity ≥ 0.55 we treat it as a candidate; ≥ 0.75 we lock it in. So 'Mall Roads' → 'Mall Road' gets corrected automatically.",
            "OCR rarely returns a perfect string. We compare each OCR'd word with our dictionary using SequenceMatcher, a string-similarity score from 0 to 1. If the similarity is high enough, we keep the closest valid area name and correct small mistakes automatically.",
        ),
        (
            "OCR can hallucinate fake PPC numbers. So before we trust any extracted section, we ask an AI language model: 'is section 380 real, and does it match this story about a stolen motorcycle?' If the AI says yes, it's accepted. If no, the FIR is flagged.",
            "OCR can hallucinate fake PPC numbers. So before we trust any extracted section, we ask an AI language model whether the section is real and whether it matches the crime story. If it does not make sense, the FIR is flagged.",
        ),
    ],
}


def replace_many(text: str, replacements: list[tuple[str, str]], file_path: Path) -> str:
    updated = text
    for old, new in replacements:
        old_variants = [old, old.replace("'", "&apos;")]
        new_variants = [new, new.replace("'", "&apos;")]

        if old_variants[0] in updated:
            updated = updated.replace(old_variants[0], new_variants[0], 1)
            continue
        if old_variants[1] in updated:
            updated = updated.replace(old_variants[1], new_variants[1], 1)
            continue

        # Allow re-running the script after partial updates.
        if new_variants[0] in updated or new_variants[1] in updated:
            continue
        print(
            f"Warning: missing expected text in {file_path}: {old!r}",
            file=sys.stderr,
        )
    return updated


def rebuild_pptx(root: Path, pptx_path: Path) -> None:
    with zipfile.ZipFile(pptx_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(root.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(root).as_posix())


def main() -> None:
    for file_path, replacements in REPLACEMENTS.items():
        original = file_path.read_text(encoding="utf-8")
        updated = replace_many(original, replacements, file_path)
        if updated != original:
            file_path.write_text(updated, encoding="utf-8")
            print(f"Updated {file_path}")
        else:
            print(f"No changes needed for {file_path}")

    rebuild_pptx(EXTRACTED_ROOT, PPTX_PATH)
    print(f"Rebuilt presentation: {PPTX_PATH}")


if __name__ == "__main__":
    main()
