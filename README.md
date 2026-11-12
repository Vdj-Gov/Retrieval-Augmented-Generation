# RAG

RAG experiments and tutorials.

- **[`RAG-Tutorials-main/pageindex_app`](RAG-Tutorials-main/pageindex_app)**: 📑 a Streamlit app for document Q&A. You upload PDFs and ask questions. It uses PageIndex (vectorless, tree-based RAG) with Groq LLMs.
- **[`PageIndex_Vectorless_RAG_CrashCourse (1).ipynb`](<RAG-Tutorials-main/PageIndex_Vectorless_RAG_CrashCourse (1).ipynb>)**: a notebook walkthrough of the same pipeline, using the ISO/IEC 27001 standard as the example document.
- The other notebooks and `src/` cover classic vector RAG (FAISS, Chroma, Typesense), RAG evaluation, and agentic RAG.

## Setup
```powershell
cp RAG-Tutorials-main/.env.example RAG-Tutorials-main/.env   # then fill in your keys
pip install -r RAG-Tutorials-main/pageindex_app/requirements.txt
streamlit run RAG-Tutorials-main/pageindex_app/app.py
```

`.env` is git-ignored, so keys are never committed.

