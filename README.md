# Code Quiz

A Python CLI that fetches your GitHub repos, sends the code to Groq LLM, and quizzes you on it interactively. Built to help developers understand their own codebase better and prepare for technical interviews.

## How it works

1. Lists all your GitHub repos
2. You pick a repo by number
3. Script fetches all code files (.py .js .swift .ts .html .css)
4. Lists all fetched files -- pick one to focus on or press Enter for all files
5. Groq generates a conceptual quiz question about your code
6. You answer in the terminal
7. Groq evaluates your answer and gives detailed feedback
8. Three possible outcomes:
   - **Correct** -- option to move to the next question
   - **Partial** -- option to retry, then move on
   - **Incorrect** -- option to retry, then move on
9. Repeat until you type `quit` or choose to stop
10. Session summary shows your score: correct, partial, incorrect, total
11. Option to save the session as a JSON file for future reference

## Why this exists

Developers often understand their code while writing it but struggle to explain it out loud -- which is exactly what technical interviews require. This tool quizzes you on your own repos so you can practice articulating decisions, patterns, and logic in your actual codebase.

## Tech stack

- Python 3.10+
- [PyGithub](https://github.com/PyGithub/PyGithub) — GitHub API client
- [Groq](https://console.groq.com) — LLM API for question generation and answer evaluation
- [python-dotenv](https://github.com/theskumar/python-dotenv) — environment variable management

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/geoClink/code-quiz.git
cd code-quiz
```

### 2. Create virtual environment

```bash
python3 -m venv venv
```

### 3. Activate virtual environment

Always activate before running the script:

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Add your API keys

Create a `.env` file in the project root:

```bash
touch .env
```

Add your keys:
GITHUB_TOKEN=your_github_token_here
GROQ_API_KEY=your_groq_api_key_here

**Getting a GitHub token:**
- Go to github.com/settings/tokens
- Click Generate new token (classic)
- Check the `repo` scope (read-only is fine)
- Copy the token immediately

**Getting a Groq API key:**
- Go to console.groq.com
- Sign up for a free account
- Click API Keys in the sidebar
- Create a new key and copy it

### 6. Run the quiz

```bash
python3 quiz.py
```

### Optional: create a shortcut command

Run this once to create a `quiz` command you can use from anywhere:

```bash
echo 'alias quiz="cd ~/code-quiz && source venv/bin/activate && python3 quiz.py"' >> ~/.zshrc
source ~/.zshrc
```

Then just type:

```bash
quiz
```

## Project roadmap

- Phase 1: Python CLI (current)
- Phase 2: SwiftUI iOS app with Keychain key storage
- Phase 3: MCP tool for Local LLM Speaker project

## Related projects

- [local-llm-speaker](https://github.com/geoClink/local-llm-speaker) — the speaker project this will eventually integrate with