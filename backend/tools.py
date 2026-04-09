import requests
import json
from functools import lru_cache
from typing import List, Dict, Any, Optional, Set

ACAD_YEAR = "2023-2024"  # Defaulting to 23-24 as 24-25 might not be fully populated yet
BASE_URL = f"https://api.nusmods.com/v2/{ACAD_YEAR}"

class NUSModsClient:
    @staticmethod
    @lru_cache(maxsize=1)
    def get_all_modules() -> List[Dict[str, Any]]:
        """Fetch brief info for all modules."""
        url = f"{BASE_URL}/moduleList.json"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return []

    @staticmethod
    @lru_cache(maxsize=500)
    def get_module_details(module_code: str) -> Optional[Dict[str, Any]]:
        """Fetch full details for a specific module."""
        url = f"{BASE_URL}/modules/{module_code}.json"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None

def search_modules(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search for modules by code or title."""
    all_modules = NUSModsClient.get_all_modules()
    query = query.upper()
    results = []
    for mod in all_modules:
        if query in mod['moduleCode'] or query in mod['title'].upper():
            results.append(mod)
            if len(results) >= limit:
                break
    return results

def check_prerequisites(prereq_tree: Any, taken_modules: Set[str]) -> bool:
    """
    Recursively evaluates the NUSMods prereqTree.
    """
    if not prereq_tree:
        return True
    
    if isinstance(prereq_tree, str):
        # Handle simple module code (possibly with variants like CS1010%)
        module_code = prereq_tree.split(':')[0]  # Remove grade requirements if any
        if "%" in module_code:
            prefix = module_code.replace("%", "")
            return any(m.startswith(prefix) for m in taken_modules)
        return module_code in taken_modules
    
    if isinstance(prereq_tree, dict):
        if "and" in prereq_tree:
            return all(check_prerequisites(child, taken_modules) for child in prereq_tree["and"])
        if "or" in prereq_tree:
            return any(check_prerequisites(child, taken_modules) for child in prereq_tree["or"])
        if "nOf" in prereq_tree:
            # Format: {"nOf": [n, [list_of_reqs]]}
            n, reqs = prereq_tree["nOf"]
            passed = sum(1 for child in reqs if check_prerequisites(child, taken_modules))
            return passed >= n

    return False

def check_timetable_conflicts(module_codes: List[str], semester: int = 1) -> Dict[str, Any]:
    """
    Checks for timetable conflicts among a list of modules.
    Simplified version for prototype: checks if any slots overlap.
    """
    slots = []  # List of (day, start_time, end_time, module_code, lesson_type)
    
    module_data = []
    for code in module_codes:
        details = NUSModsClient.get_module_details(code)
        if not details:
            continue
        
        # Get timetable for specific semester
        sem_data = next((s for s in details.get('semesterData', []) if s['semester'] == semester), None)
        if not sem_data or 'timetable' not in sem_data:
            continue
        
        module_data.append({
            "code": code,
            "timetable": sem_data['timetable']
        })

    # This is complex because students pick ONE slot per lesson type.
    # For a simple check, we return the timetable data and let the Agent/UI handle it,
    # or identify modules that ONLY have overlapping slots.
    return module_data

if __name__ == "__main__":
    # Quick test
    print(f"Searching for 'CS1101S': {search_modules('CS1101S')}")
    tree = {"and": ["CS1010", {"or": ["MA1101R", "MA1521"]}]}
    print(f"Checking prereqs (taken MA1101R, CS1010): {check_prerequisites(tree, {'CS1010', 'MA1101R'})}")
    print(f"Checking prereqs (taken CS1010): {check_prerequisites(tree, {'CS1010'})}")
