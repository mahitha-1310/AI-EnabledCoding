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
