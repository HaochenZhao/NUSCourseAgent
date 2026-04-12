"""
NUS Course Agent — Tool-calling conversational agent.

Single agentic loop: LLM decides which tools to call and when.
Streams SSE events to the frontend.
Compatible with any OpenAI-compatible API (OpenRouter, qingyuntop, etc.)
"""

import json
import logging
import os
from typing import Any, Dict, Generator, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from tools import (
    NUSModsClient,
    tool_build_timetable,
    tool_get_module_details,
    tool_search_modules,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
LLM_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.qingyuntop.top/v1")
LLM_API_KEY = os.getenv("OPENAI_API_KEY", "")
MAX_ITERATIONS = 15

# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function-calling schema)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_modules",
            "description": (
                "Search or list NUS modules. Use 'prefix' to filter by code prefix "
                "(e.g. 'CS5' for all CS5xxx). Use 'query' for keyword search in code+title. "
                "Both can be combined. Pass query='' with a prefix to list all modules "
                "under that prefix."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword(s) to search, e.g. 'machine learning'. Empty string to skip keyword filter.",
                    },
                    "prefix": {
                        "type": "string",
                        "description": "Module code prefix filter, e.g. 'CS5', 'CS'. Omit to search all codes.",
                    },
                    "semester": {
                        "type": "integer",
                        "description": "Filter to modules offered in this semester (1 or 2). Omit for both.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_module_details",
            "description": (
                "Get full details for specific modules: description, workload, "
                "lecture schedule (tutorials are excluded), exam dates, and "
                "prerequisite information (undergrad only). "
                "Always call this before recommending modules."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "module_codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Module codes to look up, e.g. ['CS5228', 'CS5340'].",
                    },
                },
                "required": ["module_codes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_timetable",
            "description": (
                "Validate that a set of modules have no lecture time conflicts and "
                "produce the weekly timetable for the UI to render. "
                "ALWAYS call this as the final step when recommending a course plan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "module_codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "The final list of recommended module codes.",
                    },
                },
                "required": ["module_codes"],
            },
        },
    },
]

TOOL_STATUS = {
    "search_modules": "Searching modules...",
    "get_module_details": "Fetching module details...",
    "build_timetable": "Building timetable...",
}

# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------


def build_system_prompt(profile: Dict[str, Any]) -> str:
    is_postgrad = profile.get("level", "").lower() == "postgraduate"
    year = profile.get("year", 1)
    semester = profile.get("semester", 1)

    prompt = f"""\
You are the NUS Course Selection Assistant. You help students at the National \
University of Singapore find and plan courses for their upcoming semester.

STUDENT CONTEXT
---------------
Programme        : {profile.get("programme", "Not specified")}
Level            : {profile.get("level", "Not specified")}
Year of study    : {year}
Eligible courses : {profile.get("pool_description", "Not specified")}
Semester         : {semester}

COURSE LEVEL GUIDELINES
-----------------------
"""

    if is_postgrad:
        prompt += """\
This student is a postgraduate student.
Recommend 5xxx and 6xxx level courses.
"""
    else:
        prompt += f"""\
This student is a Year {year} undergraduate.
Prioritize {year}xxx level courses, but adjacent levels are acceptable.
For example, a Year 3 student should primarily see 3xxx courses,
but 4xxx is fine if it fits their interest.
"""

    prompt += """
HOW TO WORK
-----------
1. Use search_modules to find candidates within the student's eligible pool.
2. Use get_module_details to get full information on promising candidates.
   - Read the lecture times carefully. DO NOT recommend modules whose
     lectures overlap. Compare every pair of lecture slots before deciding.
"""

    if not is_postgrad:
        prompt += """\
   - Read the prerequisite_text for each module. If a module has
     prerequisites, TELL the student what they are and ASK whether
     they have completed them. Do not assume. Do not skip this.
     If the student says they cannot meet a prerequisite, find a
     replacement and re-verify the timetable.
"""

    prompt += """\
3. Once you have a conflict-free set, call build_timetable to confirm
   and generate the visual timetable for the student.

RULES
-----
- NEVER invent module information. Every fact must come from tool results.
- NEVER recommend modules with overlapping lecture times.
- ALWAYS call build_timetable as the final step when giving a course plan.
"""

    if not is_postgrad:
        prompt += """\
- ALWAYS show prerequisite requirements to the student and ask for
  confirmation before finalizing.
"""

    prompt += """\
- Be concise. Use markdown tables when comparing modules.
- Include NUSMods links so the student can verify details.
- When the student asks for adjustments, use conversation history.
  Only call the tools you need, don't redo everything from scratch.
"""

    return prompt


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------


class ToolExecutor:
    def __init__(self, profile: Dict[str, Any]) -> None:
        self.profile = profile
        self.semester = int(profile.get("semester", 1))
        self.is_postgrad = profile.get("level", "").lower() == "postgraduate"
        self.timetable_payload: Optional[Dict[str, Any]] = None

    def execute(self, name: str, args: Dict[str, Any]) -> Any:
        try:
            if name == "search_modules":
                return tool_search_modules(
                    query=args.get("query", ""),
                    prefix=args.get("prefix", ""),
                    semester=args.get("semester") or self.semester,
                )
            elif name == "get_module_details":
                return tool_get_module_details(
                    module_codes=args.get("module_codes", []),
                    semester=self.semester,
                    is_postgrad=self.is_postgrad,
                )
            elif name == "build_timetable":
                result = tool_build_timetable(
                    module_codes=args.get("module_codes", []),
                    semester=self.semester,
                )
                if result.get("feasible"):
                    self.timetable_payload = result
                return result
            else:
                return {"error": f"Unknown tool: {name}"}
        except Exception as exc:
            logger.warning("Tool %s failed: %s", name, exc)
            return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class CourseAgent:
    def __init__(self) -> None:
        self.client: Optional[OpenAI] = None
        if LLM_API_KEY:
            self.client = OpenAI(
                base_url=LLM_BASE_URL,
                api_key=LLM_API_KEY,
            )
        self.model = LLM_MODEL

    def test_connection(self) -> Dict[str, Any]:
        if not self.client:
            return {"success": False, "error": "API key missing"}
        try:
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Reply OK"}],
                max_tokens=20,
            )
            return {"success": True, "model": self.model}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def stream_chat(
        self,
        message: str,
        profile: Dict[str, Any],
        history: List[Dict[str, str]],
    ) -> Generator[Dict[str, Any], None, None]:
        if not self.client:
            yield {"event": "error", "data": {"message": "OpenRouter API key not configured."}}
            return

        system_prompt = build_system_prompt(profile)
        executor = ToolExecutor(profile)

        # Build messages
        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for item in history:
            role = item.get("role", "")
            content = item.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        # Agentic loop
        last_choice = None

        for iteration in range(MAX_ITERATIONS):
            is_last = iteration == MAX_ITERATIONS - 1
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOLS if not is_last else None,
                    tool_choice="auto" if not is_last else None,
                    max_tokens=4096,
                    temperature=0.3,
                )
            except Exception as exc:
                yield {"event": "error", "data": {"message": f"LLM call failed: {exc}"}}
                return

            choice = response.choices[0]
            last_choice = choice

            if choice.finish_reason != "tool_calls":
                break

            tool_calls = choice.message.tool_calls or []
            if not tool_calls:
                break

            # Append assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": choice.message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            })

            # Execute tools
            for tc in tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                yield {
                    "event": "tool_call",
                    "data": {
                        "name": fn_name,
                        "display": TOOL_STATUS.get(fn_name, f"Running {fn_name}..."),
                    },
                }

                result = executor.execute(fn_name, fn_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

        # Emit final text
        final_text = (last_choice.message.content or "") if last_choice else ""
        if final_text:
            yield {"event": "text_delta", "data": {"text": final_text}}

        # Emit timetable if build_timetable succeeded
        if executor.timetable_payload is not None:
            yield {"event": "timetable", "data": executor.timetable_payload}

        yield {"event": "done", "data": {}}
