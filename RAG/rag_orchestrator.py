import os
import re
from typing import List, Dict, Any
import subprocess
# from groq import Groq

from rag.vector_store import get_collection
from rag.embedder import embed_query


class RAGRetriever:
    def __init__(self) -> None:
        # api_key = os.getenv("GROQ_API_KEY")
        # if not api_key:
        #     raise RuntimeError("GROQ_API_KEY not found in environment")

        self.collection = get_collection()
        # self.client = Groq(api_key=api_key)
        # self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    def retrieve(self, query: str, k: int = 6) -> List[Dict[str, Any]]:
        q_emb = embed_query(query)

        results = self.collection.query(
            query_embeddings=[q_emb],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        retrieved: List[Dict[str, Any]] = []

        for doc, meta, dist in zip(docs, metas, distances):
            meta = meta or {}

            retrieved.append({
                "file_path": meta.get("file_path", "unknown_file"),
                "branch": meta.get("branch", "unknown_branch"),
                "start_line": meta.get("start_line", "?"),
                "end_line": meta.get("end_line", "?"),
                "repo_url": meta.get("repo_url", ""),
                "distance": dist,
                "document": doc
            })

        return retrieved

    def build_context(self, chunks: List[Dict[str, Any]]) -> str:
        parts = []

        for i, chunk in enumerate(chunks, start=1):
            part = (
                f"[Chunk {i}]\n"
                f"FILE: {chunk['file_path']}\n"
                f"BRANCH: {chunk['branch']}\n"
                f"LINES: {chunk['start_line']}-{chunk['end_line']}\n"
                f"CODE:\n"
                f"{chunk['document']}"
            )
            parts.append(part)

        return "\n\n".join(parts)

    def build_prompt(self, query: str, chunks: List[Dict[str, Any]], mode: str = "code") -> str:
        context = self.build_context(chunks)

        if mode == "code":
            return f"""You are a senior software engineer working on a legacy repository.

Use ONLY the repository context below.

Repository Context
------------------
{context}

Task
----
{query}

Instructions
------------
1. Generate only raw C code grounded in the retrieved repository context
2. Reuse naming, style, and conventions from the repository
3. Do not invent unsupported APIs, files, or functions
4. Do not include explanation
5. Do not include markdown
6. Do not include code fences
7. Output only C code
8. If the context is insufficient, explicitly say what is missing
"""

        return f"""You are a senior software engineer analyzing a legacy codebase.

Use ONLY the repository context below.

Repository Context
------------------
{context}

Question
--------
{query}

Instructions
------------
1. Answer only from the retrieved repository context
2. Mention file names when relevant
3. Do not make unsupported claims
4. If the context is insufficient, say so clearly
5. Return your response in exactly this format:

EXPLANATION:
<your grounded answer here>"""

    def generate(self, prompt: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a repository-grounded code assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1400,
        )

        content = completion.choices[0].message.content
        return content or ""

    def extract_code_block(self, text: str) -> str:
        match = re.search(r"```[a-zA-Z0-9_+-]*\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def extract_explanation(self, text: str) -> str:
        if "EXPLANATION:" in text and "TARGET_FILE:" in text:
            return text.split("EXPLANATION:", 1)[1].split("TARGET_FILE:", 1)[0].strip()

        if "EXPLANATION:" in text and "CODE:" in text:
            return text.split("EXPLANATION:", 1)[1].split("CODE:", 1)[0].strip()

        if "EXPLANATION:" in text:
            return text.split("EXPLANATION:", 1)[1].strip()

        return text.strip()

    def extract_target_file(self, text: str) -> str:
        if "TARGET_FILE:" in text and "CODE:" in text:
            return text.split("TARGET_FILE:", 1)[1].split("CODE:", 1)[0].strip()

        if "TARGET_FILE:" in text:
            return text.split("TARGET_FILE:", 1)[1].strip()

        return ""

    def simple_code_beautify(self, code: str) -> str:
        if not code:
            return ""

        lines = [line.rstrip() for line in code.splitlines()]

        cleaned = []
        previous_blank = False

        for line in lines:
            is_blank = line.strip() == ""
            if is_blank and previous_blank:
                continue
            cleaned.append(line)
            previous_blank = is_blank

        return "\n".join(cleaned).strip()
    
    def format_c_code(self, code: str) -> str:
        if not code:
            return ""

        try:
            result = subprocess.run(
                ["clang-format"],
                input=code,
                text=True,
                capture_output=True,
                check=True
            )
            return result.stdout.strip()
        except Exception:
            return code

    def run(self, query: str, mode: str = "code", k: int = 6) -> Dict[str, Any]:
        print("Retrieving context...")
        chunks = self.retrieve(query=query, k=k)

        print("Building prompt...")
        prompt = self.build_prompt(query=query, chunks=chunks, mode=mode)

        print("Calling Groq LLM...")
        raw_output = self.generate(prompt)

        context_strings = []
        for chunk in chunks:
            context_strings.append(
                f"{chunk['file_path']} (lines {chunk['start_line']}-{chunk['end_line']})\n{chunk['document']}"
            )

        if mode == "code":
            code = raw_output.strip()
            code = self.simple_code_beautify(code)
            code = self.format_c_code(code)

            return {
                "mode": "code",
                "query": query,
                "code": code,
                "context": context_strings
                
            }

        answer = self.extract_explanation(raw_output)

        return {
            "mode": "text",
            "query": query,
            "code": "",
            "answer": answer,
            "context": context_strings
        }