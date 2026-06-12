from github import Github, Auth
import os
import json
from datetime import datetime
from groq import Groq


def load_env():
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


load_env()


def load_previous_questions(repo_name):
    asked = []
    sessions_dir = "sessions"
    if not os.path.exists(sessions_dir):
        return asked
    for filename in os.listdir(sessions_dir):
        if filename.startswith(repo_name) and filename.endswith(".json"):
            with open(f"{sessions_dir}/{filename}") as f:
                data = json.load(f)
                for q in data.get("questions", []):
                    asked.append(q["question"])
    return asked


def load_flagged_questions(repo_name):
    flagged = []
    sessions_dir = "sessions"
    if not os.path.exists(sessions_dir):
        return flagged
    for filename in os.listdir(sessions_dir):
        if filename.startswith(repo_name) and filename.endswith(".json"):
            with open(f"{sessions_dir}/{filename}") as f:
                data = json.load(f)
                for q in data.get("questions", []):
                    if q.get("flagged"):
                        flagged.append(q["question"])
    return flagged


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

try:
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    user = g.get_user()
    repos = list(user.get_repos())
except Exception as e:
    print(f"Failed to connect to GitHub: {e}")
    exit()

print("\nYour repos:\n")
for i, repo in enumerate(repos):
    print(f"{i + 1}. {repo.name}")

while True:
    choice = input("\nEnter a number to select a repo: ").strip()
    if not choice.isdigit():
        print("Please enter a number.")
        continue
    index = int(choice) - 1
    if index < 0 or index >= len(repos):
        print(f"Please enter a number between 1 and {len(repos)}.")
        continue
    selected_repo = repos[index]
    print(f"\nYou selected: {selected_repo.name}")
    break

print(f"\nFetching code files from {selected_repo.name}...\n")

code_contents = []
try:
    contents = selected_repo.get_contents("")
    while contents:
        file = contents.pop(0)
        if file.type == "dir":
            try:
                contents.extend(selected_repo.get_contents(file.path))
            except Exception:
                pass
        elif file.name.endswith((".py", ".js", ".swift", ".ts", ".html", ".css")):
            try:
                code_contents.append(
                    f"--- {file.path} ---\n{file.decoded_content.decode('utf-8')}"
                )
            except Exception:
                pass
except Exception as e:
    print(f"Failed to fetch repo contents: {e}")
    exit()

if not code_contents:
    print(f"\nNo supported code files found in {selected_repo.name}.")
    print("Supported types: .py .js .swift .ts .html .css")
    print("Please run the script again and pick a different repo.\n")
    exit()

combined_code_all = "\n\n".join(code_contents)

print(f"\nFetched {len(code_contents)} code files\n")
print("Pick a file to focus on, or press Enter to use all files:\n")

for i, content in enumerate(code_contents):
    filename = content.split("\n")[0].replace("--- ", "").replace(" ---", "")
    print(f"{i + 1}. {filename}")

while True:
    file_choice = input("\nFile number (or press Enter for all): ").strip()
    if not file_choice:
        combined_code = combined_code_all
        print(f"\nUsing all files -- {len(combined_code)} characters total\n")
        break
    if not file_choice.isdigit():
        print("Please enter a number or press Enter for all files.")
        continue
    selected_index = int(file_choice) - 1
    if selected_index < 0 or selected_index >= len(code_contents):
        print(f"Please enter a number between 1 and {len(code_contents)}.")
        continue
    combined_code = code_contents[selected_index]
    selected_file = combined_code.split("\n")[0].replace("--- ", "").replace(" ---", "")
    print(f"\nFocusing on: {selected_file}\n")
    break

print("\nSelect difficulty:\n")
print("1. Beginner      -- what does this do, how does this work")
print("2. Intermediate  -- why was this approach chosen, what does this pattern mean")
print("3. Advanced      -- what would break if you changed this, what are the tradeoffs\n")

difficulty_choice = input("Enter 1, 2, or 3 (or press Enter for Intermediate): ").strip()

if difficulty_choice == "1":
    difficulty = "beginner"
    difficulty_instruction = "Ask beginner-friendly questions focused on what code does and how it works. Keep questions simple and clear."
elif difficulty_choice == "3":
    difficulty = "advanced"
    difficulty_instruction = "Ask advanced questions focused on tradeoffs, what would break if something changed, architecture decisions, and edge cases."
else:
    difficulty = "intermediate"
    difficulty_instruction = "Ask intermediate questions focused on why decisions were made, what patterns are being used, and how components interact."

print("\nSelect a topic to focus on (or press Enter for any topic):\n")
print("1. Error handling")
print("2. Data flow")
print("3. API design")
print("4. Authentication")
print("5. Performance")
print("6. Any topic\n")

topic_choice = input("Enter 1-6 (or press Enter for any): ").strip()

topics = {
    "1": "error handling",
    "2": "data flow",
    "3": "API design",
    "4": "authentication",
    "5": "performance"
}

topic = topics.get(topic_choice, None)
topic_instruction = f"Focus your questions specifically on {topic} in the code." if topic else ""

try:
    client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    print(f"Failed to connect to Groq: {e}")
    exit()

previous_questions = load_previous_questions(selected_repo.name)
flagged_questions = load_flagged_questions(selected_repo.name)

if flagged_questions:
    print(f"\nYou flagged these questions for review last session:\n")
    for q in flagged_questions:
        print(f"  - {q}")
    print()

if previous_questions:
    history_note = "You have already asked these questions in previous sessions, do not repeat them:\n" + "\n".join(f"- {q}" for q in previous_questions)
else:
    history_note = ""

conversation_history = [
    {
        "role": "system",
        "content": f"You are a senior developer quizzing a junior developer on their own code. Ask one conceptual question at a time. Never ask about specific line numbers. Keep questions clear and concise. Never repeat a question you have already asked in this conversation. {difficulty_instruction} {topic_instruction} {history_note}"
    }
]

session_log = {
    "repo": selected_repo.name,
    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "difficulty": difficulty,
    "topic": topic or "any",
    "questions": []
}


def ask_question():
    conversation_history.append({
        "role": "user",
        "content": f"Here is the code from my GitHub repo called {selected_repo.name}:\n\n{combined_code[:40000]}\n\nAsk me one quiz question about this code. Do not repeat any previous questions."
    })
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=conversation_history
        )
        question = response.choices[0].message.content
        conversation_history.append({
            "role": "assistant",
            "content": question
        })
        return question
    except Exception as e:
        print(f"\nFailed to generate question: {e}")
        return None


def evaluate_answer(question, answer):
    conversation_history.append({
        "role": "user",
        "content": f"My answer to your question was: {answer}\n\nWas my answer correct, partially correct, or incorrect? Be encouraging but honest. Tell me what I got right, what I missed, and give the full explanation. End your response with exactly one word on the last line: CORRECT, PARTIAL, or INCORRECT."
    })
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=conversation_history
        )
        feedback = response.choices[0].message.content
        conversation_history.append({
            "role": "assistant",
            "content": feedback
        })
        return feedback
    except Exception as e:
        print(f"\nFailed to evaluate answer: {e}")
        return None


print("\nGenerating first question...\n")
question = ask_question()
if not question:
    print("Could not generate a question. Check your Groq API key and try again.")
    exit()
print(f"Question: {question}\n")

correct = 0
partial = 0
incorrect = 0
streak = 0
current_entry = {"question": question, "attempts": [], "flagged": False}

while True:
    answer = input("Your answer (or type 'quit', 'hint', 'flag', 'explain'): ").strip()

    if answer.lower() == "quit":
        if current_entry["attempts"]:
            session_log["questions"].append(current_entry)
        break

    if answer.lower() == "hint":
        conversation_history.append({
            "role": "user",
            "content": "Give me a hint for this question without revealing the full answer. Just a nudge in the right direction."
        })
        try:
            hint_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=conversation_history
            )
            hint = hint_response.choices[0].message.content
            conversation_history.append({"role": "assistant", "content": hint})
            print(f"\nHint: {hint}\n")
        except Exception as e:
            print(f"Failed to get hint: {e}")
        continue

    if answer.lower() == "flag":
        current_entry["flagged"] = True
        print("\nFlagged for review. You will see this question again next session.\n")
        session_log["questions"].append(current_entry)
        another = input("Next question? (y/n): ")
        if another.lower() != "y":
            break
        question = ask_question()
        if not question:
            break
        print(f"\nQuestion: {question}\n")
        current_entry = {"question": question, "attempts": [], "flagged": False}
        continue

    feedback = evaluate_answer(question, answer)
    if not feedback:
        print("Could not evaluate answer. Try again.")
        continue

    print(f"\nFeedback: {feedback}\n")

    current_entry["attempts"].append({
        "answer": answer,
        "feedback": feedback
    })

    followup = input("Type 'explain' for a deeper dive, or press Enter to continue: ").strip().lower()
    if followup == "explain":
        conversation_history.append({
            "role": "user",
            "content": "Explain this concept in plain English with a simple example. Assume I am still learning."
        })
        try:
            explain_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=conversation_history
            )
            explanation = explain_response.choices[0].message.content
            conversation_history.append({"role": "assistant", "content": explanation})
            print(f"\nExplanation: {explanation}\n")
        except Exception as e:
            print(f"Failed to get explanation: {e}")

    last_line = feedback.strip().split("\n")[-1].strip().upper()

    if "INCORRECT" in last_line:
        result = "incorrect"
        incorrect += 1
        streak = 0
    elif "PARTIAL" in last_line:
        result = "partial"
        partial += 1
        streak = 0
    else:
        result = "correct"
        correct += 1
        streak += 1
        if streak == 3:
            print("3 in a row -- you are on a roll!\n")
        elif streak == 5:
            print("5 in a row -- you clearly know this codebase.\n")
        elif streak >= 7:
            print(f"{streak} in a row -- exceptional.\n")

    current_entry["result"] = result

    if result == "correct":
        session_log["questions"].append(current_entry)
        another = input("Next question? (y/n): ")
        if another.lower() != "y":
            break
        question = ask_question()
        if not question:
            break
        print(f"\nQuestion: {question}\n")
        current_entry = {"question": question, "attempts": [], "flagged": False}

    elif result in ("partial", "incorrect"):
        retry = input("Want to try again? (y/n): ")
        if retry.lower() == "y":
            print(f"\nSame question: {question}\n")
        else:
            session_log["questions"].append(current_entry)
            another = input("Next question? (y/n): ")
            if another.lower() != "y":
                break
            question = ask_question()
            if not question:
                break
            print(f"\nQuestion: {question}\n")
            current_entry = {"question": question, "attempts": [], "flagged": False}

print(f"\n--- Session Summary ---")
print(f"Repo:      {selected_repo.name}")
print(f"Difficulty: {difficulty}")
print(f"Topic:     {topic or 'any'}")
print(f"Correct:   {correct}")
print(f"Partial:   {partial}")
print(f"Incorrect: {incorrect}")
print(f"Total:     {correct + partial + incorrect}")
print(f"Best streak: {streak}")

session_log["summary"] = {
    "correct": correct,
    "partial": partial,
    "incorrect": incorrect,
    "total": correct + partial + incorrect,
    "best_streak": streak
}

save = input("\nSave this session? (y/n): ")
if save.lower() == "y":
    os.makedirs("sessions", exist_ok=True)
    filename = f"sessions/{selected_repo.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(session_log, f, indent=2)
    print(f"Session saved to {filename}")

print("\nGood session! Keep building.")