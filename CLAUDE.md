# Guidelines for Claude Agents

This repository contains a Flask application for managing film shot assets. Use this document to quickly understand the project layout and common tasks, including project-specific rules and behaviors for Claude Code when working on this codebase.

## Task Management

- **Remove completed tasks from markdown files** - After completing a task documented in IMPROVEMENTS.md or similar files, remove it from the document to keep the list current and actionable. Don't bother marking them DONE or FIXED, just delete them after completion.
- **Write implementation plans in the source document** - When asked to create an implementation plan, add it directly to the document where the task/feature is defined (e.g., add plans to FEATURES.md, not a separate file).

## Directory overview

- `app/` – Main application package
  - `routes/` – Flask route blueprints
  - `services/` – Logic for file handling, project and shot management
  - `config/` – App-level constants
  - `utils.py` – Small helper utilities
  - `templates/` – HTML templates
  - `static/` – Static files and generated thumbnails
- `run.py` – Entry point to launch the Flask server
- `tests/` – Sample data and placeholder test directory (no active tests)

## Getting started

1. Install dependencies with `pip install -r requirements.txt`.
2. Start the development server using `python run.py`.

## Testing

Run `pytest -q` from the repository root. There are currently no automated tests, but this command should complete successfully and is used to verify the environment.

## Contributing

- Follow standard PEP 8 style when modifying Python code.
- Keep route logic in `app/routes/` and business logic in `app/services/`.
- When adding thumbnails or uploads, ensure paths are resolved using helpers in `app.utils` to avoid path traversal.
- Store new static or template assets within their respective directories.

This `CLAUDE.md` applies to the entire repository.

## Before Making Changes

1. Read existing code before modifying
2. Check for existing utilities/hooks that handle the use case
3. Follow existing patterns in the codebase
4. Remove any code that becomes unused after changes

## Post-Edit Verification

- **Always run `git diff --stat` after each edit** to confirm only the intended file and lines changed. The `code-simplifier` plugin (enabled globally) can automatically reformat or strip large sections of CSS, Python, and other files after an edit. If unexpected changes appear, revert immediately with `git checkout -- <file>` before making further edits.
- When editing CSS or JS files, verify the file size and structure are intact after the edit completes.
