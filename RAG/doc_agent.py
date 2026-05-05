import os
from groq import Groq  # type: ignore
from dotenv import load_dotenv
from rag.github_loader import fetch_repo_files  # ✅ REQUIRED IMPORT

load_dotenv()

def generate_documentation_for_repo(repo_url: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "❌ GROQ_API_KEY not found. Put it in your .env file."

    client = Groq(api_key=api_key)

    if not repo_url or not isinstance(repo_url, str):
        return "❌ repo_url is required."

    files = fetch_repo_files(repo_url)
    if not files:
        return "No supported code files found in the repository."

    code_context = "\n\n".join(
        f"### File: {name}\n```text\n{content}\n```"
        for name, content in files
    )

    prompt = f"""
You are an expert software documentation agent.
Create a clean, structured, readable technical documentation report.

Repository: {repo_url}

Analyze the following code:

{code_context}

Return ONLY the final documentation. Use markdown headings and bullets.
"""

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a code documentation expert."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=1500,
    )

    return completion.choices[0].message.content or "⚠️ Empty response from model."
