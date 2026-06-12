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

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

auth = Auth.Token(GITHUB_TOKEN)
g = Github(auth=auth)
user = g.get_user()

repos = list(user.get_repos())

print("\nYour repos:\n")
for i, repo in enumerate(repos):
    print(f"{i + 1}. {repo.name}")

choice = input("\nEnter a number to select a repo: ")
selected_repo = repos[int(choice) - 1]
print(f"\nYou selected: {selected_repo.name}")

print(f"\nFetching code files from {selected_repo.name}...\n")

code_contents = []
contents = selected_repo.get_contents("")

while contents:
    file = contents.pop(0)
    if file.type == "dir":
        contents.extend(selected_repo.get_contents(file.path))
    elif file.name.endswith((".py", ".js", ".swift", ".ts", ".html", ".css")):
        try:
            code_contents.append(
                f"--- {file.path} ---\n{file.decoded_content.decode('utf-8')}"
            )
        except Exception:
            pass

combined_code_all = "\n\n".join(code_contents)

print(f"\nFetched {len(code_contents)} code files\n")
print("Pick a file to focus on, or press Enter to use all files:\n")

for i, content in enumerate(code_contents):
    filename = content.split("\n")[0].replace("--- ", "").replace(" ---", "")
    print(f"{i + 1}. {filename}")

file_choice = input("\nFile number (or press Enter for all): ").strip()

if file_choice and file_choice.isdigit():
    selected_index = int(file_choice) - 1
    combined_code = code_contents[selected_index]
    selected_file = combined_code.split("\n")[0].replace("--- ", "").replace(" ---", "")
    print(f"\nFocusing on: {selected_file}\n")
else:
    combined_code = combined_code_all
    print(f"\nUsing all files -- {len(combined_code)} characters total\n")

client = Groq(api_key=GROQ_API_KEY)

previous_questions = load_previous_questions(selected_repo.name)

if previous_questions:
    history_note = "You have already asked these questions in previous sessions, do not repeat them:\n" + "\n".join(f"- {q}" for q in previous_questions)
else:
    history_note = ""

conversation_history = [
    {
        "role": "system",
        "content": f"You are a senior developer quizzing a junior developer on their own code. Ask one conceptual question at a time. Focus on why decisions were made, what a function does, or how a pattern works. Never ask about specific line numbers. Keep questions clear and concise. Never repeat a question you have already asked in this conversation. {history_note}"
    }
]

session_log = {
    "repo": selected_repo.name,
    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "questions": []
}

def ask_question():
    conversation_history.append({
        "role": "user",
        "content": f"Here is the code from my GitHub repo called {selected_repo.name}:\n\n{combined_code[:40000]}\n\nAsk me one quiz question about this code. Do not repeat any previous questions."
    })
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

def evaluate_answer(question, answer):
    conversation_history.append({
        "role": "user",
        "content": f"My answer to your question was: {answer}\n\nWas my answer correct, partially correct, or incorrect? Be encouraging but honest. Tell me what I got right, what I missed, and give the full explanation. End your response with exactly one word on the last line: CORRECT, PARTIAL, or INCORRECT."
    })
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

print("Generating first question...\n")
question = ask_question()
print(f"Question: {question}\n")

correct = 0
partial = 0
incorrect = 0
current_entry = {"question": question, "attempts": []}

while True:
    answer = input("Your answer (or type 'quit' to exit): ")

    if answer.lower() == "quit":
        if current_entry["attempts"]:
            session_log["questions"].append(current_entry)
        break

    feedback = evaluate_answer(question, answer)
    print(f"\nFeedback: {feedback}\n")

    current_entry["attempts"].append({
        "answer": answer,
        "feedback": feedback
    })

    last_line = feedback.strip().split("\n")[-1].strip().upper()

    if "INCORRECT" in last_line:
        result = "incorrect"
        incorrect += 1
    elif "PARTIAL" in last_line:
        result = "partial"
        partial += 1
    else:
        result = "correct"
        correct += 1

    current_entry["result"] = result

    if result == "correct":
        session_log["questions"].append(current_entry)
        another = input("Next question? (y/n): ")
        if another.lower() != "y":
            break
        question = ask_question()
        print(f"\nQuestion: {question}\n")
        current_entry = {"question": question, "attempts": []}

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
            print(f"\nQuestion: {question}\n")
            current_entry = {"question": question, "attempts": []}

print(f"\n--- Session Summary ---")
print(f"Correct:   {correct}")
print(f"Partial:   {partial}")
print(f"Incorrect: {incorrect}")
print(f"Total:     {correct + partial + incorrect}")

session_log["summary"] = {
    "correct": correct,
    "partial": partial,
    "incorrect": incorrect,
    "total": correct + partial + incorrect
}

save = input("\nSave this session? (y/n): ")
if save.lower() == "y":
    os.makedirs("sessions", exist_ok=True)
    filename = f"sessions/{selected_repo.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(session_log, f, indent=2)
    print(f"Session saved to {filename}")

print("\nGood session! Keep building.")