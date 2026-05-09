import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from openai import OpenAI


class UnitTestingStage:
    """
Main unit testing stage responsible for:
- Discovering C source and header files
- Generating unit tests with an LLM
- Compiling generated tests
- Running generated executables
- Logging results
"""
    def __init__(self, output_dir: str, project_root: str, prompt_text: Optional[str] = None):
        """
        Initialize the unit testing stage.

        Parameters:
            output_dir  -> directory used for generated tests/results
            project_root -> root directory of the project being tested
            prompt_text -> original user request used to guide unit test generation
        """
        self.project_root = os.path.abspath(project_root)
        self.output_dir = os.path.abspath(output_dir)
        self.prompt_text = prompt_text.strip() if prompt_text else None

        self.generated_code_dir = self.project_root
        self.unit_test_dir = self.output_dir

        os.makedirs(self.output_dir, exist_ok=True)

        self._function_cache: Dict[str, Set[str]] = {}

    def set_prompt_text(self, prompt_text: Optional[str]) -> None:
        """Update the user request used to steer unit test generation."""
        self.prompt_text = prompt_text.strip() if prompt_text else None

    def run(self) -> Dict:
        """
        Main entry point for the unit testing stage.

        Returns:
            Dictionary containing unit test execution results.
        """
        if not self._unit_tests_exist():
            print("No unit tests found. Generating tests...")
            self.generate_tests(self.generated_code_dir)
        else:
            print("Unit tests already exist. Skipping generation.")

        return self.run_generated_tests(self.generated_code_dir, self.unit_test_dir)

    def generate_tests(self, generated_code_dir: str) -> None:
        """
        Generate unit tests for discovered source files using an LLM.

        Parameters:
            generated_code_dir -> root source directory
        """
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_API_BASE")
        model = os.getenv("OPENAI_API_MODEL")

        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        if not model:
            raise RuntimeError("OPENAI_API_MODEL is not set.")
        if not os.path.isdir(generated_code_dir):
            raise RuntimeError(f"Source code directory does not exist: {generated_code_dir}")

        timeout = float(os.getenv("MODEL_TIMEOUT", 120))
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

        c_files = self._collect_c_files(generated_code_dir)
        h_files = self._collect_h_files(generated_code_dir)

        if not c_files:
            raise RuntimeError(f"No C source files found in {generated_code_dir}")

        all_source_code = {}

        for source_path in c_files + h_files:
            relative_name = self._relative_path(source_path, generated_code_dir)
            try:
                code = Path(source_path).read_text(encoding="utf-8", errors="ignore")
                all_source_code[relative_name] = code
            except Exception as e:
                print(f"Warning: Could not read {relative_name}: {e}")

        all_functions = self._extract_functions_from_code(all_source_code)
        files_with_main = self._identify_files_with_main(all_functions)

        for source_path in c_files:
            relative_name = self._relative_path(source_path, generated_code_dir)

            if relative_name in files_with_main:
                print(f"Skipping {relative_name} - contains main().")
                continue

            code = Path(source_path).read_text(encoding="utf-8", errors="ignore")
            functions_in_file = self._extract_functions_from_code({relative_name: code})

            prompt = self._build_generation_prompt(
                relative_name=relative_name,
                source_code=code,
                available_files=list(all_source_code.keys()),
                functions_to_test=sorted(functions_in_file.get(relative_name, set())),
                related_code=(
                    chr(10).join(
                        f"// {fname}:{chr(10)}{content[:500]}..."
                        for fname, content in list(all_source_code.items())
                        if fname != relative_name
                    )
                    if len(all_source_code) > 1
                    else "// No additional files"
                ),
            )

            max_retries = 3
            test_code = None
            last_error = None

            for attempt in range(max_retries):
                if attempt > 0:
                    prompt_with_error = f"""
Previous attempt failed with compilation error:
{last_error}

Please regenerate the test and fix the compilation error.

{prompt}
"""
                else:
                    prompt_with_error = prompt

                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a strict C unit test generator."
                        },
                        {
                            "role": "user",
                            "content": prompt_with_error
                        }
                    ],
                    temperature=0.1
                )

                test_code = response.choices[0].message.content or ""
                test_code = self._strip_markdown_fences(test_code)
                test_code = self._review_and_repair_test(
                    client=client,
                    model=model,
                    test_code=test_code,
                    source_relative_name=relative_name,
                    source_code=code,
                    available_files=list(all_source_code.keys()),
                    functions_to_test=sorted(functions_in_file.get(relative_name, set())),
                    related_code=(
                        chr(10).join(
                            f"// {fname}:{chr(10)}{content[:500]}..."
                            for fname, content in list(all_source_code.items())
                            if fname != relative_name
                        )
                        if len(all_source_code) > 1
                        else "// No additional files"
                    ),
                )
                if self._has_brittle_output_assertions(test_code):
                    test_code = self._soften_brittle_output_assertions(
                        client=client,
                        model=model,
                        test_code=test_code,
                        source_relative_name=relative_name,
                        source_code=code,
                        available_files=list(all_source_code.keys()),
                        functions_to_test=sorted(functions_in_file.get(relative_name, set())),
                        related_code=(
                            chr(10).join(
                                f"// {fname}:{chr(10)}{content[:500]}..."
                                for fname, content in list(all_source_code.items())
                                if fname != relative_name
                            )
                            if len(all_source_code) > 1
                            else "// No additional files"
                        ),
                    )

                if not self._looks_like_c_test_code(test_code):
                    last_error = "Generated output does not look like valid C test code."
                    continue

                try:
                    self._validate_generated_test(test_code, generated_code_dir)
                    break
                except RuntimeError as e:
                    last_error = str(e)

                    if attempt < max_retries - 1:
                        print(f"Attempt {attempt + 1} failed, retrying: {last_error}")
                    else:
                        raise RuntimeError(
                            f"Failed to generate compilable test after {max_retries} attempts. "
                            f"Last error: {last_error}"
                        )

            if test_code is None:
                raise RuntimeError("Failed to generate test code.")

            safe_test_name = self._safe_test_file_name(relative_name)
            output_path = os.path.join(self.unit_test_dir, safe_test_name)

            os.makedirs(self.unit_test_dir, exist_ok=True)
            Path(output_path).write_text(test_code, encoding="utf-8")
            print(f"Generated tests for {relative_name}, saved to {output_path}")

    def _build_generation_prompt(
        self,
        relative_name: str,
        source_code: str,
        available_files: List[str],
        functions_to_test: List[str],
        related_code: str,
    ) -> str:
        user_request = self.prompt_text or "No original user request was provided."
        function_lines = chr(10).join(f"- {func}" for func in functions_to_test) or "- All public functions"
        file_lines = chr(10).join(f"- {fname}" for fname in available_files)

        return f"""
You are a strict C unit test generator that ensures comprehensive test coverage.

CRITICAL REQUIREMENTS:
- Include <assert.h>, <stdio.h>, <stdlib.h>, <limits.h>, <string.h>, <ctype.h>, <math.h> as needed
- If the test uses malloc(), free(), calloc(), realloc(), or exit(), include <stdlib.h>
- Do NOT use signal handling, sigaction(), sigemptyset(), sigsetjmp(), siglongjmp(), or SIGFPE.
- Do NOT use POSIX file descriptor operations: dup(), fileno(), pipe(), fork(), or any function requiring <unistd.h>.
- Use ONLY standard C99 library functions. All tests must compile with -std=c99 and no POSIX extensions.
- Include project headers when available, but never include project implementation files such as .c files.
- Assume project source files are compiled and linked separately. Do not pull implementation code into the test with #include of source files.
- Prefer testing behavior through the public API instead of relying on private struct layout or internal helper functions.
- Declare function prototypes if no header file exists.
- Provide a main() function that returns 0 on success.
- TEST ALL FUNCTIONS in the source file with multiple test cases.
- Do NOT use markdown fences.
- Output ONLY raw C code.
- Before writing each assertion, reason carefully about the program state after every prior operation.
- Do not assert any state change, return value, output value, or side effect unless it follows directly from the implementation and the sequence of operations performed by the test.
- Treat stateful APIs conservatively: verify transitions using the code's actual contract and control flow, not intuition.
- Be especially careful about off-by-one errors, incorrect assumptions about ordering, stale state, invalid edge-case expectations, and mismatches between the prompt and the implementation.
- For functions that print output, avoid brittle exact-format assertions unless the prompt or source code explicitly defines a required output format.
- Prefer semantic output checks such as presence of key values, relative ordering, emptiness, or observable state changes over full-string equality on incidental whitespace or labels.

ORIGINAL USER REQUEST:
{user_request}

Use the user request to infer expected behavior, edge cases, constraints, and safety properties.
Prefer tests that check the contract implied by the request, not just superficial execution.

AVAILABLE SOURCE FILES:
{file_lines}

FUNCTIONS TO TEST:
{function_lines}

C Source Code to Test:
{source_code}

Follow-up Code:
{related_code}
"""

    def _review_and_repair_test(
        self,
        client: OpenAI,
        model: str,
        test_code: str,
        source_relative_name: str,
        source_code: str,
        available_files: List[str],
        functions_to_test: List[str],
        related_code: str,
    ) -> str:
        """
        Ask the LLM to critique the generated test for logical mistakes and repair it.

        This does not guarantee perfect tests, but it catches many state-transition
        mistakes before the test is accepted.
        """
        review_prompt = f"""
You are a skeptical reviewer of C unit tests.

Your job is to reject tests that compile but make incorrect logical assumptions.
Be especially strict about:
- incorrect assertions about state after sequences of operations
- off-by-one errors
- incorrect assumptions about ordering, mutation, persistence, or reset behavior
- assertions about counters, indexes, lengths, flags, capacities, or output values that are not justified by the code
- asserting behavior that is not supported by the provided source code or user request
- including project implementation files such as .c files instead of headers
- relying on private implementation details when the public API is sufficient
- brittle exact stdout assertions that depend on incidental formatting, labels, spacing, or newline style rather than required behavior

Review the candidate test below against the source code and the original request.
If you find any logical mistake, rewrite the full test so the logic is correct.
If the test is already logically sound, return it unchanged.

Return ONLY raw C code. Do NOT explain your reasoning. Do NOT use markdown fences.

ORIGINAL USER REQUEST:
{self.prompt_text or "No original user request was provided."}

SOURCE FILE UNDER TEST:
{source_relative_name}

FUNCTIONS TO TEST:
{chr(10).join(f"- {func}" for func in functions_to_test) or "- All public functions"}

AVAILABLE SOURCE FILES:
{chr(10).join(f"- {fname}" for fname in available_files)}

C SOURCE CODE TO TEST:
{source_code}

FOLLOW-UP CODE:
{related_code}

CANDIDATE TEST CODE:
{test_code}
"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a rigorous reviewer of unit tests. "
                        "You must correct logical mistakes in stateful tests before they are accepted."
                    )
                },
                {
                    "role": "user",
                    "content": review_prompt
                }
            ],
            temperature=0.0
        )

        reviewed_code = response.choices[0].message.content or ""
        reviewed_code = self._strip_markdown_fences(reviewed_code)
        return reviewed_code or test_code

    def _soften_brittle_output_assertions(
        self,
        client: OpenAI,
        model: str,
        test_code: str,
        source_relative_name: str,
        source_code: str,
        available_files: List[str],
        functions_to_test: List[str],
        related_code: str,
    ) -> str:
        """
        Rewrite tests that overfit incidental stdout formatting.

        This preserves meaningful output checks while avoiding failures caused by
        unspecified labels, spacing, or newline style.
        """
        review_prompt = f"""
You are reviewing a C unit test for brittle output assertions.

Your job is to rewrite the test only if it relies on exact stdout formatting
that is not explicitly required by the user request or the source code.

Rules:
- Keep strong behavioral assertions.
- If output format is not explicitly specified, do NOT require exact whole-string equality on labels, spacing, or newline layout.
- Prefer checking for key values, relative ordering, emptiness, or other semantic properties.
- If exact formatting is clearly part of the contract, preserve exact checks.
- Return ONLY raw C code. Do NOT explain your reasoning. Do NOT use markdown fences.

ORIGINAL USER REQUEST:
{self.prompt_text or "No original user request was provided."}

SOURCE FILE UNDER TEST:
{source_relative_name}

FUNCTIONS TO TEST:
{chr(10).join(f"- {func}" for func in functions_to_test) or "- All public functions"}

AVAILABLE SOURCE FILES:
{chr(10).join(f"- {fname}" for fname in available_files)}

C SOURCE CODE TO TEST:
{source_code}

FOLLOW-UP CODE:
{related_code}

CANDIDATE TEST CODE:
{test_code}
"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a rigorous reviewer of unit tests. "
                        "Reduce brittle output-format assertions while preserving real behavioral checks."
                    )
                },
                {
                    "role": "user",
                    "content": review_prompt
                }
            ],
            temperature=0.0
        )

        softened_code = response.choices[0].message.content or ""
        softened_code = self._strip_markdown_fences(softened_code)
        return softened_code or test_code

    def run_generated_tests(self, generated_code_dir: str, unit_test_dir: str) -> Dict:
        """
        Compile and execute generated unit tests.

        Parameters:
            generated_code_dir -> root source directory
            unit_test_dir      -> directory containing generated tests

        Returns:
            Dictionary containing execution results and logs.
        """
        results = {
            "passed": False,
            "tests_run": 0,
            "failures": 0,
            "errors": []
        }

        if not os.path.isdir(unit_test_dir):
            results["errors"].append({
                "stage": "setup",
                "file": None,
                "message": f"Unit test directory does not exist: {unit_test_dir}"
            })
            return results

        if not os.path.isdir(generated_code_dir):
            results["errors"].append({
                "stage": "setup",
                "file": None,
                "message": f"Source code directory does not exist: {generated_code_dir}"
            })
            return results

        test_files = self._collect_c_files(unit_test_dir)

        if not test_files:
            results["errors"].append({
                "stage": "setup",
                "file": None,
                "message": "No C test files found."
            })
            return results

        all_source_files = self._collect_c_files(generated_code_dir)

        all_source_code = {}

        for source_path in all_source_files:
            relative_name = self._relative_path(source_path, generated_code_dir)
            try:
                code = Path(source_path).read_text(encoding="utf-8", errors="ignore")
                all_source_code[relative_name] = code
            except Exception as e:
                print(f"Warning: Could not read {relative_name}: {e}")

        all_functions = self._extract_functions_from_code(all_source_code)
        files_with_main = self._identify_files_with_main(all_functions)

        object_files = {}

        for source_path in all_source_files:
            relative_name = self._relative_path(source_path, generated_code_dir)
            object_name = self._safe_object_file_name(relative_name)
            object_path = os.path.join(self.output_dir, object_name)

            compile_cmd = [
                "clang",
                "-std=c99",
                "-g",
                "-Wall",
                "-Wextra",
                "-c",
                source_path,
                *self._include_flags(generated_code_dir),
                "-o",
                object_path
            ]

            compile_proc = subprocess.run(compile_cmd, capture_output=True, text=True)

            if compile_proc.returncode != 0:
                results["errors"].append({
                    "stage": "compile",
                    "file": relative_name,
                    "message": f"Failed to compile {relative_name}: {compile_proc.stderr.strip()}"
                })
                continue

            object_files[relative_name] = object_path
            print(f"Compiled {relative_name} to {object_path}")

        for test_path in test_files:
            test_file_name = os.path.basename(test_path)
            test_code = Path(test_path).read_text(encoding="utf-8", errors="ignore")

            included_sources = self._find_included_project_sources(test_code, generated_code_dir)
            if included_sources:
                results["errors"].append({
                    "stage": "test_structure",
                    "file": test_file_name,
                    "message": (
                        "Generated test includes project implementation file(s), which would "
                        "cause duplicate definitions when source objects are linked separately: "
                        + ", ".join(included_sources)
                    )
                })
                continue

            source_path = self._match_test_to_source(test_file_name, generated_code_dir)

            if source_path is None:
                results["errors"].append({
                    "stage": "mapping",
                    "file": test_file_name,
                    "message": f"Could not find matching source file for {test_file_name}"
                })
                continue

            object_files_to_link = [
                obj_path
                for source_name, obj_path in object_files.items()
                if source_name not in files_with_main
            ]

            executable = os.path.join(
                self.output_dir,
                os.path.splitext(test_file_name)[0]
            )

            link_cmd = [
                "clang",
                "-std=c99",
                "-g",
                "-Wall",
                "-Wextra",
                test_path,
                *object_files_to_link,
                *self._include_flags(generated_code_dir),
                "-o",
                executable
            ]

            link_proc = subprocess.run(link_cmd, capture_output=True, text=True)

            if link_proc.returncode != 0:
                results["errors"].append({
                    "stage": "link",
                    "file": test_file_name,
                    "message": link_proc.stderr.strip()
                })
                continue

            try:
                run_proc = self._run_executable(executable)
                results["tests_run"] += 1

                if run_proc.returncode != 0:
                    results["failures"] += 1
                    results["errors"].append({
                        "stage": "run",
                        "file": test_file_name,
                        "message": (
                            run_proc.stderr.strip()
                            or run_proc.stdout.strip()
                            or f"Executable exited with code {run_proc.returncode}"
                        )
                    })

            except subprocess.TimeoutExpired:
                results["failures"] += 1
                results["errors"].append({
                    "stage": "run",
                    "file": test_file_name,
                    "message": "Execution timeout"
                })

        results["passed"] = (
            results["tests_run"] > 0
            and results["failures"] == 0
            and len(results["errors"]) == 0
        )

        return results

    def _unit_tests_exist(self) -> bool:
        """
        Check whether generated C unit tests already exist.

        Returns:
            True if unit tests exist, otherwise False.
        """
        if not os.path.isdir(self.unit_test_dir):
            return False

        return any(
            path.is_file() and path.suffix == ".c"
            for path in Path(self.unit_test_dir).rglob("*.c")
        )

    def _collect_c_files(self, directory: str) -> List[str]:
        """
        Recursively collect all .c files from a directory.
        """
        if not os.path.isdir(directory):
            return []

        return [
            str(path)
            for path in Path(directory).rglob("*.c")
            if path.is_file()
        ]

    def _collect_h_files(self, directory: str) -> List[str]:
        """
        Recursively collect all .h files from a directory.
        """
        if not os.path.isdir(directory):
            return []

        return [
            str(path)
            for path in Path(directory).rglob("*.h")
            if path.is_file()
        ]

    def _get_include_dirs(self, root_dir: str) -> List[str]:
        """
        Collect all include directories used during compilation.
        """
        include_dirs = {os.path.abspath(root_dir)}

        for h_file in self._collect_h_files(root_dir):
            include_dirs.add(os.path.dirname(os.path.abspath(h_file)))

        return sorted(include_dirs)

    def _include_flags(self, root_dir: str) -> List[str]:
        """
        Convert include directories into compiler -I flags.
        """
        flags = []

        for include_dir in self._get_include_dirs(root_dir):
            flags.extend(["-I", include_dir])

        return flags

    def _relative_path(self, file_path: str, root_dir: str) -> str:
        """
        Convert an absolute path into a path relative to the project root.
        """
        return os.path.relpath(os.path.abspath(file_path), os.path.abspath(root_dir))

    def _safe_test_file_name(self, relative_source_path: str) -> str:
        """
        Convert a source file path into a filesystem-safe test filename.
        """
        safe_name = relative_source_path.replace(os.sep, "__").replace("/", "__")
        return f"test_{safe_name}"

    def _safe_object_file_name(self, relative_source_path: str) -> str:
        """
        Convert a source file path into a filesystem-safe object filename.
        """
        safe_name = relative_source_path.replace(os.sep, "__").replace("/", "__")
        return safe_name.replace(".c", ".o")

    def _extract_functions_from_code(self, code_dict: Dict[str, str]) -> Dict[str, Set[str]]:
        """
        Extract function names from C source code using regular expressions.

        Returns:
            Dictionary mapping filenames to extracted function names.
        """
        functions = {}

        func_pattern = re.compile(
            r'(?:^|\n)\s*'
            r'(?:static\s+)?'
            r'(?:inline\s+)?'
            r'(?:const\s+)?'
            r'(?:void|int|char|float|double|long|short|unsigned|struct|FILE\*)'
            r'\s*\*?\s+'
            r'(\w+)'
            r'\s*\([^)]*\)\s*\{',
            re.MULTILINE
        )

        for filename, code in code_dict.items():
            matches = func_pattern.findall(code)
            functions[filename] = set(matches)

        return functions

    def _identify_files_with_main(self, functions: Dict[str, Set[str]]) -> Set[str]:
        """
        Identify source files that contain a main() function.
        """
        files_with_main = set()

        for filename, func_set in functions.items():
            if "main" in func_set:
                files_with_main.add(filename)

        return files_with_main

    def _match_test_to_source(self, test_file_name: str, generated_code_dir: str) -> Optional[str]:
        """
        Match a generated test filename back to its original source file.
        """
        all_sources = self._collect_c_files(generated_code_dir)

        cleaned_test_name = (
            test_file_name.lower()
            .replace("test_", "")
            .replace("_code", "")
            .replace(".c", "")
        )

        cleaned_test_name = cleaned_test_name.replace("__", "/")

        for source_path in all_sources:
            relative_source = self._relative_path(source_path, generated_code_dir)
            normalized_relative = relative_source.lower().replace("\\", "/").replace(".c", "")

            if cleaned_test_name == normalized_relative:
                return source_path

        for source_path in all_sources:
            source_base = os.path.basename(source_path).lower().replace(".c", "")

            if cleaned_test_name.replace("/", "__") == source_base:
                return source_path

            if source_base in cleaned_test_name or cleaned_test_name in source_base:
                return source_path

        return None

    def _run_executable(self, executable: str) -> subprocess.CompletedProcess:
        """
        Execute a compiled unit test binary with timeout protection.
        """
        return subprocess.run(
            [executable],
            capture_output=True,
            text=True,
            timeout=5
        )

    def _strip_markdown_fences(self, text: str) -> str:
        """
        Remove markdown code fences from generated LLM output.
        """
        text = re.sub(r"```[a-zA-Z]*", "", text)
        text = text.replace("```", "")
        return text.strip()

    def _looks_like_c_test_code(self, text: str) -> bool:
        """
        Perform a basic validation check that generated output resembles C test code.
        """
        required_signals = ["main(", "#include", "assert"]
        return all(signal in text for signal in required_signals)

    def _has_brittle_output_assertions(self, test_code: str) -> bool:
        """
        Heuristically detect tests that overfit exact captured stdout formatting.
        """
        captures_stdout = "capture_stdout" in test_code or "tmpfile()" in test_code
        exact_string_compare = (
            "strcmp(output, expected)" in test_code
            or "strcmp(expected, output)" in test_code
            or "strncmp(output, expected" in test_code
            or "strncmp(expected, output" in test_code
        )
        return captures_stdout and exact_string_compare

    def _find_included_project_sources(self, test_code: str, generated_code_dir: str) -> List[str]:
        """
        Return project source files that are directly included by the test.

        Tests should include headers, not implementation files, because the stage
        compiles source files separately and links them afterward.
        """
        source_files = {
            self._relative_path(path, generated_code_dir).replace("\\", "/").lower()
            for path in self._collect_c_files(generated_code_dir)
        }
        include_pattern = re.compile(r'^\s*#\s*include\s*"([^"]+)"', re.MULTILINE)
        included_sources = []

        for include_target in include_pattern.findall(test_code):
            normalized = include_target.replace("\\", "/").lower()
            if not normalized.endswith(".c"):
                continue

            basename = os.path.basename(normalized)
            if normalized in source_files or any(
                path == basename or path.endswith("/" + basename)
                for path in source_files
            ):
                included_sources.append(include_target)

        return sorted(set(included_sources))

    def _validate_generated_test(self, test_code: str, generated_code_dir: str) -> None:
        """
        Compile generated test code before saving it to disk.

        Raises:
            RuntimeError if the generated test fails compilation.
        """
        included_sources = self._find_included_project_sources(test_code, generated_code_dir)
        if included_sources:
            raise RuntimeError(
                "Generated test code includes project implementation file(s), which would cause "
                "duplicate definitions when source objects are linked separately: "
                + ", ".join(included_sources)
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".c", mode="w", encoding="utf-8") as tmp:
            tmp.write(test_code)
            tmp_path = tmp.name

        object_path = tmp_path + ".o"

        compile_cmd = [
            "clang",
            "-std=c99",
            "-g",
            "-Wall",
            "-Wextra",
            "-c",
            tmp_path,
            *self._include_flags(generated_code_dir),
            "-o",
            object_path
        ]

        try:
            compile_proc = subprocess.run(compile_cmd, capture_output=True, text=True)

            if compile_proc.returncode != 0:
                stderr = compile_proc.stderr.strip()
                headers_to_inject = []

                if (
                    any(symbol in test_code for symbol in ["malloc", "free", "calloc", "realloc"])
                    and "#include <stdlib.h>" not in test_code
                ):
                    headers_to_inject.append("#include <stdlib.h>")

                if (
                    any(const in test_code for const in [
                        "INT_MAX", "INT_MIN", "LONG_MAX", "LONG_MIN", "CHAR_MAX", "CHAR_MIN"
                    ])
                    and "#include <limits.h>" not in test_code
                ):
                    headers_to_inject.append("#include <limits.h>")

                if (
                    any(func in test_code for func in ["fabs", "sqrt", "sin", "cos", "pow"])
                    and "#include <math.h>" not in test_code
                ):
                    headers_to_inject.append("#include <math.h>")

                if headers_to_inject:
                    test_code = "\n".join(headers_to_inject) + "\n" + test_code

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".c", mode="w", encoding="utf-8") as retry_tmp:
                        retry_tmp.write(test_code)
                        retry_tmp_path = retry_tmp.name

                    retry_object_path = retry_tmp_path + ".o"

                    retry_compile_cmd = [
                        "clang",
                        "-std=c99",
                        "-g",
                        "-Wall",
                        "-Wextra",
                                "-c",
                        retry_tmp_path,
                        *self._include_flags(generated_code_dir),
                        "-o",
                        retry_object_path
                    ]

                    retry_proc = subprocess.run(retry_compile_cmd, capture_output=True, text=True)

                    try:
                        os.remove(retry_tmp_path)
                    except OSError:
                        pass

                    try:
                        os.remove(retry_object_path)
                    except OSError:
                        pass

                    if retry_proc.returncode != 0:
                        raise RuntimeError(
                            f"Generated test code failed to compile even after injecting headers "
                            f"{headers_to_inject}. Compiler error: {retry_proc.stderr.strip()}"
                        )

                else:
                    raise RuntimeError(
                        "Generated test code failed to compile before saving. "
                        f"Compiler error: {stderr}"
                    )

        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

            try:
                os.remove(object_path)
            except OSError:
                pass
