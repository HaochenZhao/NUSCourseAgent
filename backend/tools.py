"""
NUSMods data layer + three tool implementations.

Tools:
  1. search_modules   — find/list modules by keyword and/or prefix
  2. get_module_details — full info for specific modules (lectures only)
  3. build_timetable  — validate no lecture conflicts + produce weekly schedule
"""

import re
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence

import requests

# ---------------------------------------------------------------------------
# NUSMods client
# ---------------------------------------------------------------------------

REQUEST_TIMEOUT = 15


def _academic_year_candidates() -> List[str]:
    """Generate candidate academic years to try, newest first."""
    now = datetime.utcnow()
    year = now.year
    candidates = []
    for start in range(year, year - 4, -1):
        candidates.append(f"{start}-{start + 1}")
    return candidates


class NUSModsClient:
    @staticmethod
    @lru_cache(maxsize=1)
    def get_academic_year() -> str:
        for candidate in _academic_year_candidates():
            url = f"https://api.nusmods.com/v2/{candidate}/moduleList.json"
            try:
                resp = requests.get(url, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 200 and resp.json():
                    return candidate
            except requests.RequestException:
                continue
        return "2024-2025"

    @staticmethod
    @lru_cache(maxsize=1)
    def get_all_modules() -> List[Dict[str, Any]]:
        ay = NUSModsClient.get_academic_year()
        url = f"https://api.nusmods.com/v2/{ay}/moduleList.json"
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException:
            pass
        return []

    @staticmethod
    @lru_cache(maxsize=500)
    def get_module_details(module_code: str) -> Optional[Dict[str, Any]]:
        code = module_code.strip().upper()
        ay = NUSModsClient.get_academic_year()
        url = f"https://api.nusmods.com/v2/{ay}/modules/{code}.json"
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException:
            pass
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NUSMODS_COURSE_BASE = "https://nusmods.com/courses"


def _tokenize(text: str) -> List[str]:
    """Split text into lowercase tokens for matching."""
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) >= 2]


def _format_time(raw: str) -> str:
    """Convert '0830' to '08:30'."""
    if len(raw) == 4 and raw.isdigit():
        return f"{raw[:2]}:{raw[2:]}"
    return raw


def _extract_lectures(details: Dict[str, Any], semester: int) -> List[Dict[str, str]]:
    """Extract lecture-only slots for a given semester. Tutorial/Lab stripped."""
    sem_data = next(
        (s for s in details.get("semesterData", []) if s.get("semester") == semester),
        None,
    )
    if not sem_data:
        return []

    lectures = []
    seen = set()
    for lesson in sem_data.get("timetable", []):
        if lesson.get("lessonType") != "Lecture":
            continue
        day = lesson.get("day", "")
        start = _format_time(lesson.get("startTime", ""))
        end = _format_time(lesson.get("endTime", ""))
        key = f"{day} {start}-{end}"
        if key not in seen:
            seen.add(key)
            lectures.append({"day": day, "start": start, "end": end})
    return lectures


def _format_workload(workload: Any) -> Optional[str]:
    if workload is None:
        return None
    if isinstance(workload, (list, tuple)):
        return "-".join(str(v) for v in workload)
    return str(workload)


def _workload_total(workload: Any) -> Optional[float]:
    if not workload:
        return None
    try:
        if isinstance(workload, (list, tuple)):
            return sum(float(v) for v in workload)
        return sum(float(v) for v in str(workload).split("-"))
    except (ValueError, TypeError):
        return None


def _time_to_minutes(t: str) -> int:
    """Convert 'HH:MM' to minutes since midnight."""
    parts = t.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def _slots_overlap(a: Dict[str, str], b: Dict[str, str]) -> bool:
    """Check if two lecture slots overlap (same day + time intersection)."""
    if a["day"] != b["day"]:
        return False
    a_start = _time_to_minutes(a["start"])
    a_end = _time_to_minutes(a["end"])
    b_start = _time_to_minutes(b["start"])
    b_end = _time_to_minutes(b["end"])
    return a_start < b_end and b_start < a_end


# ---------------------------------------------------------------------------
# Tool 1: search_modules
# ---------------------------------------------------------------------------

def tool_search_modules(
    query: str = "",
    prefix: str = "",
    semester: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Search/list NUSMods modules by keyword and/or code prefix."""
    all_mods = NUSModsClient.get_all_modules()
    prefix_upper = prefix.strip().upper()
    terms = _tokenize(query)

    results: List[tuple] = []
    for mod in all_mods:
        code: str = mod["moduleCode"]
        title: str = mod.get("title", "")

        # prefix filter
        if prefix_upper and not code.startswith(prefix_upper):
            continue

        # semester filter
        semesters = mod.get("semesters", [])
        if semester is not None and semester not in semesters:
            continue

        # keyword scoring
        if terms:
            haystack = f"{code} {title}".lower()
            score = sum(2 if t in haystack else 0 for t in terms)
            if score == 0:
                continue
        else:
            score = 0  # no keywords = list all (sorted by code)

        results.append((score, code, title, semesters))

    results.sort(key=lambda x: (-x[0], x[1]))
    return [
        {"module_code": code, "title": title, "semesters": sems}
        for _, code, title, sems in results[:30]
    ]


# ---------------------------------------------------------------------------
# Tool 2: get_module_details
# ---------------------------------------------------------------------------

def tool_get_module_details(
    module_codes: List[str],
    semester: int,
    is_postgrad: bool,
) -> List[Dict[str, Any]]:
    """Fetch full details for modules. Tutorials stripped. Prereqs conditional."""
    results: List[Dict[str, Any]] = []

    for raw_code in module_codes[:10]:
        code = raw_code.strip().upper()
        details = NUSModsClient.get_module_details(code)
        if not details:
            results.append({"module_code": code, "error": "Module not found on NUSMods"})
            continue

        # lectures only
        lectures = _extract_lectures(details, semester)
        lecture_strings = [f"{l['day']} {l['start']}-{l['end']}" for l in lectures]

        # semester availability
        sem_data = next(
            (s for s in details.get("semesterData", []) if s.get("semester") == semester),
            None,
        )

        # exam
        has_exam = False
        exam_date = None
        if sem_data:
            raw_exam = sem_data.get("examDate")
            if raw_exam:
                has_exam = True
                exam_date = raw_exam

        # description truncation
        desc = details.get("description") or ""
        if len(desc) > 400:
            desc = desc[:400].rstrip() + "..."

        # workload
        workload_raw = details.get("workload")
        workload_str = _format_workload(workload_raw)
        workload_tot = _workload_total(workload_raw)

        entry: Dict[str, Any] = {
            "module_code": code,
            "title": details.get("title", ""),
            "description": desc,
            "module_credit": details.get("moduleCredit", "4"),
            "workload": workload_str,
            "workload_total": workload_tot,
            "lectures": lecture_strings,
            "has_exam": has_exam,
            "exam_date": exam_date,
            "semesters_offered": details.get("semesters", []),
            "nusmods_url": f"{NUSMODS_COURSE_BASE}/{code}",
        }

        # prerequisite: only for undergrad
        if not is_postgrad:
            entry["prerequisite_text"] = details.get("prerequisite") or "None"

        if not sem_data:
            entry["not_offered_this_semester"] = True

        results.append(entry)

    return results


# ---------------------------------------------------------------------------
# Tool 3: build_timetable
# ---------------------------------------------------------------------------

def tool_build_timetable(
    module_codes: List[str],
    semester: int,
) -> Dict[str, Any]:
    """Validate lecture conflicts and produce the weekly schedule."""

    # Gather all lecture slots per module
    module_lectures: Dict[str, List[Dict[str, str]]] = {}
    for raw_code in module_codes:
        code = raw_code.strip().upper()
        details = NUSModsClient.get_module_details(code)
        if not details:
            continue
        lectures = _extract_lectures(details, semester)
        module_lectures[code] = lectures

    # Check pairwise conflicts
    conflicts: List[Dict[str, str]] = []
    codes = list(module_lectures.keys())
    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            for slot_a in module_lectures[codes[i]]:
                for slot_b in module_lectures[codes[j]]:
                    if _slots_overlap(slot_a, slot_b):
                        conflicts.append({
                            "module_a": codes[i],
                            "module_b": codes[j],
                            "slot": f"{slot_a['day']} {slot_a['start']}-{slot_a['end']}",
                        })

    # Build combined schedule
    schedule: Dict[str, List[Dict[str, str]]] = {
        "Monday": [], "Tuesday": [], "Wednesday": [],
        "Thursday": [], "Friday": [], "Saturday": [],
    }
    total_hours = 0.0
    for code, lectures in module_lectures.items():
        for lec in lectures:
            day = lec["day"]
            if day in schedule:
                schedule[day].append({
                    "module_code": code,
                    "start": lec["start"],
                    "end": lec["end"],
                })
            duration = (_time_to_minutes(lec["end"]) - _time_to_minutes(lec["start"])) / 60.0
            total_hours += duration

    # Sort each day by start time
    for day in schedule:
        schedule[day].sort(key=lambda x: x["start"])

    # Remove empty days
    schedule = {day: slots for day, slots in schedule.items() if slots}

    # Exam dates
    exam_dates: Dict[str, Optional[str]] = {}
    for code in module_codes:
        code = code.strip().upper()
        details = NUSModsClient.get_module_details(code)
        if details:
            sem_data = next(
                (s for s in details.get("semesterData", []) if s.get("semester") == semester),
                None,
            )
            if sem_data and sem_data.get("examDate"):
                exam_dates[code] = sem_data["examDate"]

    return {
        "feasible": len(conflicts) == 0,
        "conflicts": conflicts,
        "schedule": schedule,
        "total_contact_hours": round(total_hours, 1),
        "exam_dates": exam_dates,
    }
