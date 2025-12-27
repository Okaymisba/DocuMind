# Project Title: Documentation Agent

## Description

This project is a Python application designed to facilitate automated documentation updates based on code analysis. The
AI documentation agent is responsible for maintaining high-quality, professional documentation for a codebase.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```
2. Set up a virtual environment (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```
3. Install the dependencies:
   ```bash
   pip install .
   ```
   Dependencies are specified in `pyproject.toml`, which includes the following libraries:
    - `openai>=1.55.0`
    - `python-dotenv>=1.0.0`

## Configuration

Before running the application, create a `.env` file in the project root. At a minimum, set the following variables:

```
OPENAI_MODEL=gpt-4o-mini  # (or your preferred model)
OPENAI_API_KEY=your-api-key-here
```

- `OPENAI_MODEL`: (Optional) Model used by the agent. Defaults to `gpt-4o-mini` if not set.
- `OPENAI_API_KEY`: (Required) Your OpenAI API key for model access.

You can add any other environment variables required by your agent implementation.

## Usage

Here are some basic usage instructions:

```bash
python main.py "<user_goal>" -v  # For verbose output
```

You can specify your user goal; for example, replace `<user_goal>` with a task such as "Analyze the codebase and update
documentation as needed." If no user goal is provided, the default will be applied.

### AI Documentation Agent Usage

The AI documentation agent is designed to:

- Identify important developer-relevant changes.
- Decide whether documentation needs to be updated.
- Update or create documentation only when it adds real value.

#### Behavioral Expectations:

- Analyze git diffs before taking any action.
- Update documentation only when justified.
- Document changes clearly and concisely to provide real value.

## Contributing

If you would like to contribute to this project, please fork the repository and create a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for more information.
