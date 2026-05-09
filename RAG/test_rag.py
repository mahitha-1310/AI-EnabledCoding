from rag.rag_orchestrator import RAGOrchestrator

rag = RAGOrchestrator()

query = input("Ask a question about the repository: ").strip()
mode = input("Mode (code/text): ").strip().lower() or "code"

result = rag.run(query=query, mode=mode)

print("\n--- MODE ---\n")
print(result["mode"])

if result["mode"] == "code":
    print("\n--- TARGET FILE ---\n")
    print(result.get("target_file", ""))

    print("\n--- EXPLANATION ---\n")
    print(result.get("explanation", ""))

    print("\n--- CODE ---\n")
    print(result.get("code", ""))
else:
    print("\n--- ANSWER ---\n")
    print(result.get("answer", ""))

print("\n--- CONTEXT ---\n")
for chunk in result.get("context", []):
    print(chunk[:500])
    print("\n" + "=" * 80 + "\n")