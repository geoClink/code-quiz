from dotenv import load_dotenv
from github import Github, Auth
import os
from groq import Groq


load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")

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

combined_code = "\n\n".join(code_contents)
print(f"Fetched {len(code_contents)} code files")
print(f"Total characters: {len(combined_code)}")

client = Groq(api_key=GROQ_API_KEY)

print("\nGenerating quiz question...\n")

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {
            "role": "system",
            "content": "You are a senior developer quizzing a junior developer on their own code. Ask one conceptual question at a time. Focus on why decisions were made, what a function does, or how a pattern works. Never ask about specific line numbers. Keep questions clear and concise.",
        },
        {
            "role": "user",
            "content": f"Here is the code from my GitHub repo called {selected_repo.name}:\n\n{combined_code[:8000]}\n\nAsk me one quiz question about this code.",
        },
    ],
)

question = response.choices[0].message.content
print(f"Question: {question}\n")

while True:
    answer = input("Your answer (or type 'quit' to exit): ")
    
    if answer.lower() == "quit":
        print("\nGood session! Keep building.")
        break

    evaluation = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a senior developer evaluating a junior developer's answer. Be encouraging but honest. Point out what was correct, what was missing, and give a brief explanation of the full answer."
            },
            {
                "role": "user",
                "content": f"Code from repo {selected_repo.name}:\n\n{combined_code[:8000]}\n\nQuestion: {question}\n\nDeveloper's answer: {answer}\n\nEvaluate this answer."
            }
        ]
    )

    feedback = evaluation.choices[0].message.content
    print(f"\nFeedback: {feedback}\n")

    another = input("Next question? (y/n): ")
    if another.lower() != "y":
        print("\nGood session! Keep building.")
        break

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a senior developer quizzing a junior developer on their own code. Ask one conceptual question at a time. Focus on why decisions were made, what a function does, or how a pattern works. Never ask about specific line numbers. Keep questions clear and concise."
            },
            {
                "role": "user",
                "content": f"Here is the code from my GitHub repo called {selected_repo.name}:\n\n{combined_code[:8000]}\n\nAsk me a different quiz question about this code. Do not repeat previous questions."
            }
        ]
    )

    question = response.choices[0].message.content
    print(f"\nQuestion: {question}\n")