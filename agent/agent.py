import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from openai import OpenAI

from functions import get_file_info, read_file, write_file
from functions._utils import normalize_path as _normalize_path

SYSTEM_PROMPT = (
    "You are an AI documentation agent responsible for maintaining high-quality, professional documentation for a codebase.\n\n"

    "Your primary input will be:\n"
    "- A git diff describing recent code changes\n"

    "Your goal is NOT to mirror the entire codebase in documentation.\n"
    "Your goal IS to:\n"
    "- Identify important, developer-relevant changes\n"
    "- Decide whether documentation needs to be updated\n"
    "- Update or create documentation only when it adds real value\n\n"

    "Documentation Scope:\n"
    "- README.md (overview, setup, usage, behavior changes)\n"
    "- Installation or configuration markdown files\n"
    "- docs/ directory files (architecture, workflows, APIs, concepts)\n"
    "- Inline docstrings for modified functions or classes\n\n"

    "Rules:\n"
    "- You MUST analyze the git diff before taking any action.\n"
    "- You MUST decide whether documentation changes are required.\n"
    "- If no meaningful documentation update is needed, explicitly state that.\n"
    "- Do NOT generate unnecessary documentation.\n"
    "- Prefer updating existing documentation files over creating new ones.\n"
    "- Create new documentation files ONLY if a new concept, workflow, or feature is introduced.\n\n"

    "Repository Navigation:\n"
    "- Use get_file_info to list contents of DIRECTORY PATHS ONLY, make sure it is not a file.\n"
    "- Use read_file to read the contents of FILES.\n"
    "- Start exploration from the root directory using get_file_info with '.'.\n"
    "- Navigate directories step by step.\n"
    "- NEVER assume a file or directory exists without checking.\n"
    "- ALWAYS verify if a path is a directory using get_file_info before using it as such.\n\n"

    "File Operations:\n"
    "- Use read_file only after confirming the path is a file.\n"
    "- Use get_file_info only for directory paths.\n"
    "- Use write_file only when documentation updates are justified.\n"
    "- When updating files, preserve existing structure and tone.\n"
    "- Modify only the minimum necessary content.\n"
    "- Don't use placeholder texts.\n\n"

    "PRE-WRITE REQUIREMENT:"
    "Before calling write_file, you MUST produce a structured change plan including:\n"
    "- File name\n"
    "- Sections to be modified or added\n"
    "- Reason for each change\n"
    "If this plan is empty, you MUST NOT write any file.\n"

    "Docstrings:\n"
    "- If a modified file contains functions or classes:\n"
    "  - Add docstrings if missing\n"
    "  - Update docstrings if behavior has changed\n"
    "- Do not rewrite entire files for minor changes.\n\n"

    "Behavioral Constraints:\n"
    "- Never hallucinate file paths.\n"
    "- Never invent undocumented features.\n"
    "- Never update documentation without evidence from the diff.\n"
    "- Always think step by step before taking actions.\n"
    "- Always verify path types (file vs directory) before operations.\n\n"

    "Output Expectations:\n"
    "- Clearly explain WHY a documentation update is needed.\n"
    "- Clearly state WHICH files will be updated and WHY.\n"
    "- Perform file operations only after reasoning is complete.\n"
)


def tool_schemas() -> List[Dict[str, Any]]:
    """OpenAI tool schemas for the three functions."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_file_info",
                "description": "List files and directories (non-recursive) for a given directory path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path to inspect."}
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file's content. Must only be used after confirming existence via get_file_info.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path of the file to read."}
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Create or update a file. Creates parent directories if missing. Only when explicitly instructed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path of the file to write."},
                        "content": {"type": "string", "description": "Full content to write into the file."},
                    },
                    "required": ["path", "content"],
                },
            },
        },
    ]


@dataclass
class Agent:
    model: str = "gpt-4o-mini"
    allow_writes: bool = False
    verbose: bool = False
    client: OpenAI = field(default_factory=OpenAI)
    discovered_files: Set[str] = field(default_factory=set)
    discovered_dirs: Set[str] = field(default_factory=set)

    def _record_discovery(self, info: Dict[str, Any]) -> None:
        current = info.get("current_path")
        if current:
            self.discovered_dirs.add(_normalize_path(current))
        for item in info.get("items", []):
            p = _normalize_path(item.get("path", ""))
            if item.get("type") == "directory":
                self.discovered_dirs.add(p)
            elif item.get("type") == "file":
                self.discovered_files.add(p)

    def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
        if name == "write_file" and not self.allow_writes:
            return (
                json.dumps({
                    "error": "write_not_allowed",
                    "message": "Write operations are disabled. Enable allow_writes to proceed.",
                }),
                None,
            )

        if name == "get_file_info":
            if self.verbose:
                print(f"Executing get_file_info with arguments: {arguments}")

            raw_path = arguments.get("path", "")
            allowed_tail = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/~ ")
            while raw_path and raw_path[-1] not in allowed_tail:
                raw_path = raw_path[:-1]
            try:
                info = get_file_info(raw_path)
                self._record_discovery(info)
                return json.dumps(info), info
            except FileNotFoundError as e:
                return json.dumps({
                    "error": "not_found",
                    "message": str(e),
                    "suggestion": "The requested path does not exist. Please verify the path and try again.",
                    "path": raw_path
                }), None

        if name == "read_file":
            if self.verbose:
                print(f"Executing read_file with arguments: {arguments}")

            norm = _normalize_path(arguments["path"])
            if norm not in self.discovered_files:
                return (
                    json.dumps({
                        "error": "file_not_confirmed",
                        "message": "Attempted to read a file that has not been confirmed via get_file_info.",
                        "path": norm,
                    }),
                    None,
                )
            content = read_file(norm)
            return json.dumps({"path": norm, "content": content}), None

        if name == "write_file":
            if self.verbose:
                print(f"Executing write_file with arguments: {arguments}")

            msg = write_file(arguments["path"], arguments["content"])
            self.discovered_files.add(_normalize_path(arguments["path"]))
            return json.dumps({"message": msg}), None

        return json.dumps({"error": "unknown_tool"}), None

    def run(self, user_message: str, max_steps: int = 20) -> str:
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        tools = tool_schemas()

        for _ in range(max_steps):
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )

            choice = resp.choices[0]
            msg = choice.message

            tool_calls = msg.tool_calls or []
            if tool_calls:
                messages.append({"role": "assistant", "content": msg.content or "",
                                 "tool_calls": [tc.model_dump(exclude_none=True) for tc in tool_calls]})
                for tc in tool_calls:
                    fn_name = tc.function.name
                    args = json.loads(tc.function.arguments or "{}")
                    result_json, _ = self._execute_tool(fn_name, args)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": fn_name,
                            "content": result_json,
                        }
                    )
                continue

            return msg.content or ""

        return "Reached max_steps without completion."
