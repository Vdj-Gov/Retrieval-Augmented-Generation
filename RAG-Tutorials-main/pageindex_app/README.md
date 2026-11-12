# 📑 PageIndex Document Q&A

Upload PDFs and ask questions. This uses **vectorless, reasoning-based RAG**: PageIndex builds a tree index of each document, and a Groq LLM reasons over that tree to find the right sections. There is no chunking and no vector database.

## Run

```powershell
cd RAG-Tutorials-main
pip install -r pageindex_app/requirements.txt
streamlit run pageindex_app/app.py
```

The keys are read from `RAG-Tutorials-main/.env`:

```
PAGEINDEX_API_KEY=...   # https://dash.pageindex.ai/api-keys
GROQ_API_KEY=...        # https://console.groq.com/keys
```

## Features
- **Upload one or more PDFs.** Each one is indexed by PageIndex cloud. Files are recognised by content hash and saved in `documents.json`, so the same PDF is never indexed twice.
- **Ask about one or several documents.** When you select several, they are searched together.
- **Two answer engines:**
  - **Groq (tree search + answer):** the Groq model picks the relevant sections, then writes an answer that cites section titles and page ranges. The app shows the sources and the model's retrieval reasoning.
  - **PageIndex Chat API:** PageIndex's hosted model answers directly. No Groq calls are made.
- **Follow-up questions** work, because recent chat history is included.
- **Optional expert routing rules** let you add domain hints that guide retrieval (for example, "specific controls → Annex A").
- **Document structure viewer** shows each document's tree.

## Files
| File | Purpose |
|---|---|
| `app.py` | Streamlit UI |
| `rag.py` | Pipeline: upload, indexing, tree search, answer |
| `documents.json` | Local record of uploaded docs (file hash → doc_id) |
| `uploads/` | Copies of the uploaded PDFs |

> On the Groq free tier you get about 8k tokens per minute. If you hit the limit, wait around 30 seconds or switch to `openai/gpt-oss-20b`.

## Deploy on Streamlit Community Cloud
1. Go to https://share.streamlit.io and click **Create app**, then **Deploy a public app from GitHub**.
2. Enter **Repository** `Vdj-Gov/RAG`, **Branch** `main`, and **Main file path** `RAG-Tutorials-main/pageindex_app/app.py`.
3. Under **Advanced settings**, set the Python version to **3.12** or newer, then paste the following into **Secrets**:
   ```toml
   PAGEINDEX_API_KEY = "..."
   GROQ_API_KEY = "..."
   APP_PASSWORD = "..."   # recommended, so strangers can't spend your API quota
   ```
4. Click **Deploy**. The app installs `pageindex_app/requirements.txt` automatically.

On the cloud, the document list is loaded from your PageIndex account, so documents you've indexed are still there after a restart.

