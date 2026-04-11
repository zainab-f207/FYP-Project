"""
AI-based Pakistani Law Section Verifier.

Provider chain (tries in order, falls back automatically):
  1. Groq       — fastest, free 14,400 req/day, llama-3.3-70b
  2. OpenRouter — free models, different infra (works if Groq blocked)

Both are FREE with no billing required.
"""

import os
import json
import logging
import re
import asyncio
from typing import Optional, Dict, Any, List

import httpx

logger = logging.getLogger(__name__)

# Law full names for better AI prompts
LAW_FULL_NAMES = {
    "PPC": "Pakistan Penal Code (Act XLV of 1860)",
    "ATA": "Anti-Terrorism Act 1997",
    "CNSA": "Control of Narcotic Substances Act 1997",
    "ARMS": "Pakistan Arms Ordinance 1965",
    "HUDOOD": "Hudood Ordinances 1979",
    "PECA": "Prevention of Electronic Crimes Act 2016",
    "EXPLOSIVE": "Explosive Substances Act 1908",
    "LSL": "Local and Special Laws (Pakistan)",
    "WOMEN_PROTECTION": "Protection of Women (Criminal Laws Amendment) Act 2006",
}

# ── Provider chain — tried in order, falls back automatically ────────────────
PROVIDERS = [
    {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "extra_headers": {},
    },
    {
        "name": "OpenRouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "meta-llama/llama-3.1-8b-instruct:free",
        "env_key": "OPENROUTER_API_KEY",
        "extra_headers": {
            "HTTP-Referer": "https://crimevision.app",
            "X-Title": "CrimeVision Law Verifier",
        },
    },
]
# ─────────────────────────────────────────────────────────────────────────────


def _error_response(error_type: str, message: str, model: str) -> Dict[str, Any]:
    """Return a standardised error dict."""
    return {
        "verified": False,
        "error": error_type,
        "ai_title": "",
        "confidence": "none",
        "explanation": message,
        "matches_current": False,
        "related_ppc": [],
        "punishment": "",
        "purpose": "",
        "raw_response": "",
        "model": model,
        "status": "error",
        "suggested_action": "review",
    }


async def scan_missing_ppc_sections(
    existing_section_numbers: List[str],
) -> Dict[str, Any]:
    """
    Scan for missing important PPC sections using ONE AI call.
    Returns up to 20 missing sections with full data ready for DB insertion.
    """
    numbers_str = ", ".join(sorted(existing_section_numbers, key=lambda x: float(x.split("-")[0]) if x.split("-")[0].isdigit() else 999))

    prompt = f"""You are a Pakistani legal database administrator. I have a law_sections database with the following PPC (Pakistan Penal Code) section numbers already recorded:

{numbers_str}

Your task: Identify up to 20 important PPC sections that are MISSING from the above list. Focus only on sections frequently cited in criminal cases in Pakistan — NOT obscure or rarely-used sections.

Respond ONLY with a valid JSON array (no markdown, no code blocks). Each element must have these exact keys:
1. "section_number": PPC section number as a string (e.g. "302", "304-A")
2. "english_title": Official English title/heading of this section (max 100 chars)
3. "punishment_summary": Brief punishment (max 15 words, e.g. "Death or life imprisonment")
4. "chapter": Chapter name (e.g. "Offences Against the Human Body")

If no important sections are missing, return an empty array: []
"""

    async with httpx.AsyncClient(timeout=60.0) as client:
        for provider in PROVIDERS:
            if not os.getenv(provider["env_key"]):
                continue
            logger.info(f"[ScanMissing] Trying {provider['name']}...")
            # Use 2500 tokens — scan returns up to 20 JSON objects, needs room
            result = await _call_provider(client, provider, prompt, max_tokens=2500)

            if result["success"]:
                raw_text = result["raw_text"]
                try:
                    # Strip markdown code fences first (```json ... ``` or ``` ... ```)
                    clean = re.sub(r'```(?:json)?\s*', '', raw_text).strip()
                    clean = re.sub(r'```\s*$', '', clean).strip()
                    # Grab the outermost JSON array
                    arr_match = re.search(r'\[[\s\S]*\]', clean)
                    if arr_match:
                        clean = arr_match.group()
                    missing = json.loads(clean)
                    if not isinstance(missing, list):
                        missing = []
                    # Validate each item has required keys
                    valid = []
                    for item in missing:
                        if isinstance(item, dict) and item.get("section_number") and item.get("english_title"):
                            valid.append({
                                "section_number": str(item["section_number"]).strip(),
                                "english_title": str(item.get("english_title", "")).strip()[:500],
                                "punishment_summary": str(item.get("punishment_summary", "")).strip()[:200],
                                "chapter": str(item.get("chapter", "")).strip()[:200],
                            })
                    return {"success": True, "missing": valid, "model": f"{result['provider_name']}/{result['model']}"}
                except json.JSONDecodeError as exc:
                    logger.error(f"[ScanMissing] JSON parse failed: {exc}\nRaw: {raw_text[:300]}")
                    return {"success": False, "error": f"AI returned invalid JSON: {exc}", "missing": []}

            etype = result.get("error_type", "unknown")
            if etype in ("network", "api_key_error", "no_key", "http_403", "http_401"):
                continue
            return {"success": False, "error": result.get("error_msg", "AI error"), "missing": []}

    return {"success": False, "error": "No AI provider available", "missing": []}


async def _call_provider(
    client: httpx.AsyncClient,
    provider: dict,
    prompt: str,
    max_tokens: int = 500,
) -> Dict[str, Any]:
    """
    Call one OpenAI-compatible provider with retry on 429.
    Returns: {success, raw_text, provider_name, model} on success
             {success:False, error_type, error_msg}      on failure
    """
    api_key = os.getenv(provider["env_key"])
    if not api_key:
        return {"success": False, "error_type": "no_key",
                "error_msg": f"{provider['env_key']} not set in backend/.env"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **provider["extra_headers"],
    }
    payload = {
        "model": provider["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }

    last_429 = None
    for attempt in range(3):
        if attempt > 0:
            wait_secs = 4 * (2 ** (attempt - 1))  # 4s then 8s
            logger.info(f"[{provider['name']}] Rate-limited, retrying in {wait_secs}s")
            await asyncio.sleep(wait_secs)

        try:
            response = await client.post(provider["url"], headers=headers, json=payload)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.NetworkError) as exc:
            logger.warning(f"[{provider['name']}] Network error: {exc}")
            return {"success": False, "error_type": "network",
                    "error_msg": f"Cannot reach {provider['name']}: {exc}"}

        if response.status_code == 429:
            last_429 = response
            continue

        if response.status_code != 200:
            raw_err = response.text
            readable = raw_err
            try:
                err_json = response.json()
                readable = (err_json.get("error", {}).get("message", "")
                            or err_json.get("message", "") or raw_err)
            except Exception:
                pass
            logger.error(f"[{provider['name']}] HTTP {response.status_code}: {readable}")
            err_lower = readable.lower()
            if response.status_code in (401, 403) or any(
                k in err_lower for k in ["invalid api key", "api key", "unauthorized", "authentication", "forbidden"]
            ):
                etype = "api_key_error"
            elif any(k in err_lower for k in ["billing", "plan", "quota", "exceeded", "limit", "resource_exhausted"]):
                etype = "daily_quota"
            else:
                etype = f"http_{response.status_code}"
            return {"success": False, "error_type": etype, "error_msg": readable}

        # 200 OK
        last_429 = None
        break

    if last_429 is not None:
        raw_err = ""
        try:
            raw_err = last_429.json().get("error", {}).get("message", last_429.text or "")
        except Exception:
            raw_err = last_429.text or ""
        is_daily = any(k in raw_err.lower() for k in ["billing", "plan", "quota", "exceeded", "daily", "resource_exhausted"])
        return {"success": False,
                "error_type": "daily_quota" if is_daily else "rate_limit",
                "error_msg": raw_err}

    try:
        raw_text = response.json()["choices"][0]["message"]["content"]
        return {"success": True, "raw_text": raw_text,
                "provider_name": provider["name"], "model": provider["model"]}
    except (KeyError, IndexError) as exc:
        return {"success": False, "error_type": "parse_error", "error_msg": str(exc)}


async def verify_law_section(
    law_type: str,
    section_number: str,
    current_title: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verify a Pakistani law section using AI.
    Tries providers in order: Groq → OpenRouter (automatic fallback).
    """
    law_name = LAW_FULL_NAMES.get(law_type, law_type)

    comparison_instruction = ""
    if current_title:
        comparison_instruction = (
            f'\n4. "matches_current": Compare with this existing title: '
            f'"{current_title}". Set true if they mean the same thing, false otherwise.'
        )

    ppc_note = (
        '5. "related_ppc": An array (can be empty []) of related Pakistan Penal Code '
        'section numbers that overlap with or are commonly charged alongside this section. '
        'E.g. ["302", "324"].'
        if law_type != "PPC"
        else '5. "related_ppc": [] (leave empty for PPC sections)'
    )

    prompt = f"""You are a Pakistani criminal law expert. I need you to verify a specific section from Pakistani law.

Law: {law_name}
Section Number: {section_number}

Please respond ONLY with a valid JSON object (no markdown, no code blocks) with these exact keys:
1. "section_title": The exact official English title/heading of this section as written in the law
2. "confidence": "high" if you are certain, "medium" if mostly sure, "low" if uncertain
3. "explanation": A brief 1-2 sentence explanation of what this section covers{comparison_instruction}
{ppc_note}
6. "punishment": The exact punishment prescribed by this section — include imprisonment term, fine amount, death penalty, or whipping as applicable. E.g. "Death, or imprisonment for life, and fine" or "Imprisonment up to 3 years, or fine, or both". Write "Not applicable" if the section is definitional.
7. "purpose": The legislative rationale — why this section exists and what harm it aims to prevent or address (1-2 sentences).

If this section does not exist in the law, set section_title to "" and confidence to "low" with explanation saying it doesn't exist, and set punishment and purpose to "".
"""

    raw_text = ""
    used_model = "unknown"
    used_provider = "unknown"
    last_failure: Dict[str, Any] = {}
    tried: List[str] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for provider in PROVIDERS:
            if not os.getenv(provider["env_key"]):
                logger.info(f"[LawVerifier] Skipping {provider['name']} — no API key")
                continue

            tried.append(provider["name"])
            logger.info(f"[LawVerifier] Trying {provider['name']}...")
            # Use 900 tokens — response now includes punishment + purpose fields
            result = await _call_provider(client, provider, prompt, max_tokens=900)

            if result["success"]:
                raw_text = result["raw_text"]
                used_model = result["model"]
                used_provider = result["provider_name"]
                break

            last_failure = result
            etype = result.get("error_type", "unknown")
            # Fall through to next provider only for network/auth issues
            if etype in ("network", "api_key_error", "no_key", "http_403", "http_401"):
                logger.warning(f"[LawVerifier] {provider['name']} failed ({etype}), trying next...")
                continue
            # For rate limits / quota / other — report immediately
            return _error_response(etype, result.get("error_msg", ""), provider["model"])
        else:
            # All providers exhausted
            if not tried:
                return _error_response(
                    "no_key",
                    "No AI provider configured.\n\n"
                    "Add at least one of these to backend/.env:\n"
                    "  GROQ_API_KEY=...       (free at console.groq.com)\n"
                    "  OPENROUTER_API_KEY=... (free at openrouter.ai)",
                    "none",
                )
            return _error_response(
                last_failure.get("error_type", "network"),
                last_failure.get("error_msg", "All AI providers failed or are unreachable."),
                "none",
            )

    # Parse the JSON response
    try:
        json_text = raw_text.strip()
        json_match = re.search(r'\{[\s\S]*\}', json_text)
        if json_match:
            json_text = json_match.group()

        parsed = json.loads(json_text)

        ai_title = parsed.get("section_title", "").strip()
        confidence = parsed.get("confidence", "low")
        explanation = parsed.get("explanation", "")
        matches = parsed.get("matches_current", None)
        related_ppc = parsed.get("related_ppc", [])
        if not isinstance(related_ppc, list):
            related_ppc = []
        punishment = str(parsed.get("punishment", "")).strip()
        purpose = str(parsed.get("purpose", "")).strip()

        if matches is None and current_title and ai_title:
            matches = (
                current_title.lower().strip() in ai_title.lower().strip()
                or ai_title.lower().strip() in current_title.lower().strip()
            )

        # Derive status and suggested_action from results (no extra AI tokens needed)
        if not ai_title:
            status = "not_found"
            suggested_action = "review"
        elif bool(matches):
            status = "correct"
            suggested_action = "keep"
        else:
            status = "incorrect"
            suggested_action = "update_title"

        return {
            "verified": bool(ai_title and confidence in ("high", "medium")),
            "ai_title": ai_title,
            "confidence": confidence,
            "explanation": explanation,
            "matches_current": bool(matches),
            "related_ppc": related_ppc,
            "punishment": punishment,
            "purpose": purpose,
            "raw_response": raw_text,
            "model": f"{used_provider}/{used_model}",
            "status": status,
            "suggested_action": suggested_action,
            "error": None,
        }

    except json.JSONDecodeError as exc:
        logger.error(f"Failed to parse AI JSON: {exc}\nRaw: {raw_text[:200]}")
        return _error_response("parse_error", f"Failed to parse AI response: {exc}", used_model)
    except Exception as exc:
        logger.error(f"verify_law_section unexpected error: {exc}")
        return _error_response(str(exc), str(exc), used_model)

