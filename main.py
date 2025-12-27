import argparse
import os

from dotenv import load_dotenv

from agent.agent import Agent


def run(user_goal: str, verbose: bool = False):
    load_dotenv()

    project_root = os.path.dirname(os.path.abspath(__file__))
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    allow_writes = True

    if verbose:
        print(f"Project root: {project_root}")
        print(f"Model: {model}")
        print(f"Allow writes: {allow_writes}")
        print(f"User goal: {user_goal}")

    agent = Agent(model=model, allow_writes=allow_writes, verbose=verbose)
    result = agent.run(user_goal)
    print(result)


def main():
    parser = argparse.ArgumentParser(description="Run the repository exploration agent")
    parser.add_argument(
        "user_goal",
        nargs="?",
        default="Please analyze the codebase and update the documentations as needed. Focus on .md files, docs/ directory, and ensure all modified code has proper docstrings.",
        help="Instruction for the agent",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    args = parser.parse_args()

    run(args.user_goal, verbose=args.verbose)


if __name__ == '__main__':
    main()
