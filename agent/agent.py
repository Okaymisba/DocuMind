import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from openai import OpenAI

from functions import get_file_info, read_file, write_file
from functions._utils import normalize_path as _normalize_path

SYSTEM_PROMPT = (
    "You are a repository exploration agent.\n\n"
    "You can navigate repositories using tools.\n"
    "You must explore directories step by step.\n\n"
    "Rules:\n"
    "- Use get_file_info to list files and directories.\n"
    "- Use get_file_info with root directory with . to  list files and directories of the root directory then navigate between files.\n"
    "- Do not assume any file exists without checking.\n"
    "- Use read_file only after confirming the file exists.\n"
    "- Use write_file only when explicitly instructed.\n"
    "- Never hallucinate file paths.\n"
    "- Think step by step before taking actions.\n"
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
        # Gate writes unless allowed
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
            info = get_file_info(raw_path)
            self._record_discovery(info)
            return json.dumps(info), info

        if name == "read_file":
            norm = _normalize_path(arguments["path"])
            # Enforce: only read known file discovered via get_file_info
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
            msg = write_file(arguments["path"], arguments["content"])
            # Record the newly written file as discovered
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

            # If the assistant responds with tool calls, execute them step-by-step
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
                # Continue loop for model to observe tool outputs
                continue

            # No tool calls: assume final answer
            return msg.content or ""

        return "Reached max_steps without completion."
