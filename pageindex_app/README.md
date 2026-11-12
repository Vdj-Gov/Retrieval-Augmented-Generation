# Retrieval-Augmented Generation (RAG)

Hands-on RAG implementations in Python, from classical vector search to vectorless, tree-based retrieval. The centrepiece is a deployable **Streamlit app for multi-document Q&A with section-level citations**. The repo also includes notebooks on agentic RAG, vector search with Typesense, and RAG evaluation.

<img width="1892" height="867" alt="image" src="https://github.com/user-attachments/assets/18f99d21-e01b-4c0d-a1a5-f769dc6ec35f" />



**Live demo:** [Open the app](https://vdj-gov-rag-rag-tutorials-mainpageindex-appapp-p11fkl.streamlit.app/) 
---

## Contents

- [Featured: PageIndex Document Q&A App](#featured-pageindex-document-qa-app)
- [Other components](#other-components)
- [Repository structure](#repository-structure)
- [Getting started](#getting-started)
- [Evaluation](#evaluation)
- [Design decisions](#design-decisions)
- [Limitations](#limitations)
- [Credits and attribution](#credits-and-attribution)
- [License](#license)

---

## Featured: PageIndex Document Q&A App

Located in [`pageindex_app/`](pageindex_app).

Most RAG systems split documents into chunks and search a vector database. This app takes a different approach: it builds a **tree index of each document's structure** (sections and subsections) with [PageIndex](https://pageindex.ai), then has an LLM reason over that tree to decide which sections to read. There is no chunking and no vector database.

**Features**
- Tree-based, vectorless retrieval over document structure
- Answers generated with Groq (`openai/gpt-oss-120b`) and cited to exact sections
- Multi-document Q&A
- Fallback to the PageIndex hosted Chat API
- One-click deployment on Streamlit Cloud

**How it works**

```mermaid
flowchart LR
    A[PDF documents] --> B[PageIndex tree index]
    Q[User question] --> C[LLM reasons over tree]
    B --> C
    C --> D[Select relevant sections]
    D --> E[LLM answers from sections]
    E --> F[Answer with section citations]
    C -. fallback .-> G[PageIndex hosted Chat API]
    G -.-> F
```

**Run locally**

```bash
pip install -r pageindex_app/requirements.txt
streamlit run pageindex_app/app.py
```

**Deploy to Streamlit Cloud**

| Setting | Value |
|---|---|
| Repository | `Vdj-Gov/Retrieval-Augmented-Generation` |
| Branch | `main` |
| Main file path | `pageindex_app/app.py` |
| Secrets | `PAGEINDEX_API_KEY`, `GROQ_API_KEY` (App Settings → Secrets) |

---

## Other components

| Path | What it covers |
|---|---|
| [`PageIndex_Vectorless_RAG_CrashCourse (1).ipynb`](<PageIndex_Vectorless_RAG_CrashCourse (1).ipynb>) | End-to-end vectorless RAG walkthrough using the ISO 27001 standard as the document |
| [`agenticrag/`](agenticrag) | Agentic RAG notebooks |
| [`1-rag_evaluation.ipynb`](1-rag_evaluation.ipynb) | RAG evaluation pipeline |
| [`typesense.ipynb`](typesense.ipynb) | Vector search with Typesense |
| [`src/`](src) | Classical vector store implementations (FAISS, Chroma) |
| [`app.py`](app.py) | <!-- TODO: one line on what the root app.py does --> |
| [`books.jsonl`](books.jsonl) | <!-- TODO: what this dataset is and which notebook uses it --> |

---

## Repository structure

```
.
├── pageindex_app/        # Streamlit vectorless Q&A app (featured)
├── agenticrag/           # Agentic RAG notebooks
├── notebook/             # Additional notebooks
├── src/                  # FAISS and Chroma implementations
├── app.py
├── 1-rag_evaluation.ipynb
├── typesense.ipynb
├── PageIndex_Vectorless_RAG_CrashCourse (1).ipynb
├── books.jsonl
├── requirements.txt
├── .env.example
└── LICENSE
```

---

## Getting started

**Prerequisites**
- Python 3.10 or newer <!-- TODO: confirm the version you used -->
- A [Groq](https://console.groq.com) API key
- A [PageIndex](https://pageindex.ai) API key

**Setup**

```bash
git clone https://github.com/Vdj-Gov/Retrieval-Augmented-Generation.git
cd Retrieval-Augmented-Generation

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env             # then add your keys
```

**Environment variables**

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | LLM calls through Groq |
| `PAGEINDEX_API_KEY` | PageIndex indexing and hosted Chat API |

Never commit your `.env` file. It is already listed in `.gitignore`.

---

## Evaluation

`1-rag_evaluation.ipynb` contains the evaluation pipeline.

<!--
TODO: Run the notebook, then replace this block with your real numbers.
Only report figures produced by an actual run. Example layout:

| Method | Metric 1 | Metric 2 | Avg latency |
|---|---|---|---|
| Vector search (FAISS) | ... | ... | ... ms |
| Vectorless (PageIndex) | ... | ... | ... ms |

State the number of questions, the documents used, and how correctness was judged.
-->

Results have not been recorded in this README yet.

---

## Design decisions

- **Vectorless retrieval for structured documents.** Standards, contracts, and reports have clear section hierarchies. Reasoning over that structure can keep sections whole, instead of cutting them into arbitrary chunks.
- **Section-level citations.** Answers point to the section they came from, so a reader can verify them.
- **Hosted API fallback.** If the local reasoning path fails, the app can fall back to PageIndex's hosted Chat API.
- **Classical baselines kept in the repo.** The FAISS and Chroma code in `src/` provides a comparison point for the tree-based approach.

---

## Limitations

- Tree-based retrieval depends on documents having a usable structure. Unstructured text may suit vector search better.
- The app relies on two external services (PageIndex and Groq), so it needs API keys and network access, and is subject to their rate limits.
- Evaluation results are limited in size and have not been published here yet.
- <!-- TODO: add anything else you observed, for example failure cases or slow queries -->

---

## Credits and attribution

This repository is a learning and experimentation project. It builds on the following open tools and resources:

- [PageIndex](https://pageindex.ai) for tree-based document indexing
- [Groq](https://groq.com) for LLM inference
- [Streamlit](https://streamlit.io) for the interface
- <!-- TODO: list every tutorial, course, or repo any notebook or code was adapted from, with links -->

Notebooks that follow an external tutorial are marked as such in the table above.

---

## License

Released under the [GPL-3.0 License](LICENSE).
