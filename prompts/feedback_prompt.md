You are writing a feedback prompt for an LLM that produced failing code.

Your feedback prompt must tell the LLM exactly what went wrong and what to fix. To do this, you **must** read and use the performance summary JSON file — they are your primary source of truth. Do not infer or generalize failures; extract them directly from the summaries.

## Your feedback prompt must:

- State precisely what failed (compilation error, runtime bug, test failure, etc.) using details from the JSON
- Quote or reference specific fields from the JSON (e.g. error messages, file names, line numbers, failed test cases) so the LLM knows exactly where the problem is
- Distinguish between categories of failure if multiple exist (e.g. a file that failed to compile vs. one with a logic bug)
- Instruct the LLM to fix only what is broken — do not suggest rewriting unaffected code
- Be direct and imperative in tone; this is a correction, not a suggestion

## Constraints:

- Do not pad the prompt with praise or preamble
- Do not speculate about causes not evidenced in the JSON
- If a field in the JSON is ambiguous, flag it explicitly in the prompt so the LLM knows to investigate that area

## Input you will receive:

The contents of one or more performance summary JSON files describing the code evaluation results.

## After applying your fixes:

Once the issues are resolved, deliver your final response to the user using the full codebase analysis format from your system prompt. Summarize what changed and why, organized by file. Do not end with a one-line confirmation.

# Summary JSON File:

{summary}
