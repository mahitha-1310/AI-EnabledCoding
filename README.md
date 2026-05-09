# HASAIM — High Assurance System AI Modernization

HASAIM is an AI-powered tool for modernizing legacy C codebases. A user uploads a C project, describes a change they want made (e.g., "add a search function to this linked list"), and an LLM agent reads the code, implements the change, and submits the result through a multi-stage validation pipeline before returning a response.

## What It Does

1. **Reads the uploaded codebase** — the agent examines all source and header files to understand the project structure before making any changes.
2. **Implements the requested change** — the agent writes new or modified `.c`/`.h` files directly into the project.
3. **Validates the result** through a five-stage pipeline:
   - **Compilation** — builds the project with `make` and verifies a clean executable is produced
   - **Static Analysis** — runs `clang-tidy` (and optionally `cppcheck`) on every source file
   - **Dynamic Analysis** — executes the binary under Valgrind to check for memory errors and leaks
   - **Formatting** — auto-formats all source files to LLVM style with `clang-format`
   - **Unit Testing** — generates assert-based C unit tests via LLM, compiles them, and runs them
4. **Returns a detailed response** — the agent reports what files it found, what it changed, and how to verify the result.

If validation fails, the agent retries automatically (up to a configurable limit) with targeted feedback from the failing stage before giving up.

---

## Running HASAIM

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Virginia Tech VPN connected ([VT VPN instructions](https://www.nis.vt.edu/ServicePortfolio/Network/RemoteAccess-VPN.html))

### Quick Start (Pre-built Image)

**Step 1 — Create your `.env` file**

Create a file named `.env` in any folder using the credentials provided in the submission document:

```env
# RAG Embedding API Key
CO_API_KEY=<provided in submission>

# Chatbot API Key
OPENAI_API_KEY=<provided in submission>

# (Optional) Extends rate limits for GitHub repo access
GITHUB_TOKEN=<provided in submission>

# Model source
OPENAI_API_BASE=https://llm-api.arc.vt.edu/api/v1/

# Model name
OPENAI_API_MODEL=gpt-oss-120b

# ChromaDB database configuration
CHROMA_MODE=local
CHROMA_COLLECTION=boeingagent_kb
CHROMA_DIR=.chroma
```

**Step 2 — Pull and run the container**

From the folder containing your `.env` file:

```bash
docker pull ghcr.io/ryanpettes/hasaim:latest
docker run -p 8501:8501 --env-file .env ghcr.io/ryanpettes/hasaim:latest
```

**Step 3 — Open the app**

Navigate to **http://localhost:8501** in your browser.

> **Note:** The first run may take a moment to start up while the container initializes.
> The VT VPN must remain connected for the duration of your session.

---

### Building from Source

If you prefer to build the image yourself:

```bash
git clone https://github.com/mahitha-1310/AI-EnabledCoding.git
cd AI-EnabledCoding
cp example.env .env   # then fill in your credentials
docker build -t hasaim .
docker run -p 8501:8501 --env-file .env hasaim
```

---

## Testing the System

The `test_projects/` directory contains four ready-to-use sample projects. Each project is a small, self-contained C codebase that compiles cleanly and is designed to exercise the full validation pipeline.

### How to Run a Test

1. **Upload the project files** — in the app's **Workspace** tab, upload all `.c`, `.h`, and `Makefile` files from one of the sample project folders below.
2. **Enter a prompt** — paste one of the sample prompts from the chatbox and press Enter.
3. **Watch the pipeline run** — progress is printed to the terminal. The UI will display the agent's response once all five validation stages complete.
4. **Download the result** — use the **Files** tab to download the modified codebase as a `.zip`.

### Sample Projects

All sample projects and their suggested prompts are documented in [`test_projects/SAMPLE_PROMPTS.md`](test_projects/SAMPLE_PROMPTS.md). A summary:

| Project            | Description                                           | What to ask for                                              |
| ------------------ | ----------------------------------------------------- | ------------------------------------------------------------ |
| `stack/`           | Integer stack backed by a fixed-size array            | `stack_swap`, `stack_clear`, `stack_contains`, `stack_copy`  |
| `linked_list/`     | Singly-linked list with add, delete, display, reverse | `swap` (node-level), `find`, `count`                         |
| `string_utils/`    | Common C string operations                            | `str_to_upper`/`str_to_lower`, `str_trim`, `str_starts_with` |
| `circular_buffer/` | Fixed-capacity FIFO circular buffer                   | `cbuf_peek`, `cbuf_flush`, `cbuf_write_overwrite`            |

Each project has two prompts (A and B) — Prompt A adds one or two focused functions, Prompt B is slightly more involved. Either works as a demo.

### What a Successful Run Looks Like

In the terminal you should see all five stages pass:

```
[Validation] Stage 1/5: Compiling project...
[Validation] Compilation: OK
[Validation] Stage 2/5: Running static analysis...
[Validation] Static analysis: OK
[Validation] Stage 3/5: Running dynamic analysis...
[Validation] Dynamic analysis: OK
[Validation] Stage 4/5: Checking formatting...
[Validation] Formatting: OK
[Validation] Stage 5/5: Running unit tests...
[Validation] Unit testing: OK
[Pipeline] Generating final response...
```

The chatbot will then respond with a structured breakdown of the files it examined, the changes it made, and how to verify the result.

These results can be further inspected by navigating to the **Files** tab and clicking the **Download Codebase** button; this will download a `.zip` file that you may then inflate, which will contain a structure similar to the following _(depending on sample project used and configuration settings)_:

```bash
output/
├── Makefile
├── artifacts
│   ├── llm_metrics
│   │   └── logs
│   └── unit_testing
│       ├── main.o
│       ├── strutil.o
│       └── test_strutil.c
├── compile_commands.json
├── logs
│   ├── compilation
│   │   ├── make_output.log
│   │   └── summary.json
│   ├── dynamic_analysis
│   │   ├── memcheck
│   │   └── summary.json
│   ├── formatting
│   │   ├── format_main.log
│   │   ├── format_strutil.log
│   │   └── summary.json
│   ├── llm_metrics
│   │   └── summary.json
│   ├── static_analysis
│   │   ├── clang-tidy
│   │   └── summary.json
│   └── unit_testing
│       ├── summary.json
│       └── unit_testing.log
├── main.c
├── strutil.c
├── strutil.h
└── strutil_demo

14 directories, 19 files
```
