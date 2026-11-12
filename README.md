# Retrieval-Augmented Generation (RAG)

A collection of RAG implementations, tutorials, and applications.

## 📑 PageIndex Vectorless Document Q&A (Streamlit)
Located in [`pageindex_app/`](pageindex_app):
- Uses **PageIndex** for tree-based indexing (no chunking, no vector DB).
- Uses **Groq** (`openai/gpt-oss-120b`) for reasoning over the document structure and answering with exact section citations.
- Includes PageIndex hosted Chat API fallback and support for multi-document Q&A.

### Running Locally
```powershell
pip install -r pageindex_app/requirements.txt
streamlit run pageindex_app/app.py
```

### Deploying to Streamlit Cloud
- **Repository:** `Vdj-Gov/Retrieval-Augmented-Generation`
- **Branch:** `main`
- **Main file path:** `pageindex_app/app.py`
- Add `PAGEINDEX_API_KEY` and `GROQ_API_KEY` in **App Settings → Secrets**.

---

## 📓 Notebooks & Tutorials
- **`PageIndex_Vectorless_RAG_CrashCourse (1).ipynb`**: End-to-end vectorless RAG crash course with ISO 27001 standard.
- **`agenticrag/`**: Agentic RAG notebooks.
- **`1-rag_evaluation.ipynb`**: RAG evaluation pipeline.
- **`typesense.ipynb`**: Vector search with Typesense.
- **`src/`**: Classical vector store implementations (FAISS, Chroma).
