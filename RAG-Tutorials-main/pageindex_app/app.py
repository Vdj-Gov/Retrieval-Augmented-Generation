"""
📑 PageIndex Document Q&A — upload PDFs, ask questions.

Run:  streamlit run pageindex_app/app.py
"""
import os

import streamlit as st

st.set_page_config(page_title="PageIndex Doc Q&A", page_icon="📑", layout="wide")

# On Streamlit Cloud, keys come from the app's Secrets; locally from .env.
try:
    for _k in ("PAGEINDEX_API_KEY", "GROQ_API_KEY", "APP_PASSWORD"):
        if _k in st.secrets:
            os.environ[_k] = str(st.secrets[_k])
except Exception:  # noqa: BLE001  (no secrets.toml locally — that's fine)
    pass

import rag  # noqa: E402  (after secrets are in the environment)

# ── Optional password gate (set APP_PASSWORD to protect your API quota) ──────
_pw = os.getenv("APP_PASSWORD")
if _pw and not st.session_state.get("authed"):
    st.title("📑 PageIndex Q&A")
    entered = st.text_input("Password", type="password")
    if entered == _pw:
        st.session_state.authed = True
        st.rerun()
    elif entered:
        st.error("Wrong password")
    st.stop()

# ── Session state ───────────────────────────────────────────────────────────
ss = st.session_state
ss.setdefault("messages", [])      # chat history: {role, content, meta?}
ss.setdefault("trees", {})         # doc_id -> tree (cache)
ss.setdefault("processed", set())  # uploaded file signatures handled this session

keys = rag.keys_status()


@st.cache_resource
def clients():
    return rag.get_pi_client(), rag.get_llm_client()


# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📑 PageIndex Q&A")
    st.caption("Vectorless, reasoning-based RAG")

    for k, ok in keys.items():
        st.write(("✅ " if ok else "❌ ") + k)
    if not all(keys.values()):
        st.error("Add the missing keys to `RAG-Tutorials-main/.env` and restart the app.")
        st.stop()

    pi, llm = clients()

    st.subheader("1 · Upload")
    files = st.file_uploader("PDF files", type=["pdf"], accept_multiple_files=True)
    for f in files or []:
        sig = f"{f.name}:{f.size}"
        if sig in ss.processed:
            continue
        data = f.getvalue()
        with st.status(f"Indexing **{f.name}**…", expanded=True) as box:
            try:
                doc_id, reused = rag.upload_pdf(pi, data, f.name)
                st.write("♻️ Already indexed — reusing" if reused else f"📤 Uploaded → `{doc_id}`")
                line = st.empty()
                status = rag.wait_until_ready(pi, doc_id, on_status=lambda s: line.write(f"⏳ Status: {s}"))
                if status == "completed":
                    box.update(label=f"✅ {f.name} ready", state="complete", expanded=False)
                else:
                    box.update(label=f"❌ {f.name}: {status}", state="error")
            except Exception as e:  # noqa: BLE001
                box.update(label=f"❌ {f.name} failed", state="error")
                st.exception(e)
        ss.processed.add(sig)

    st.subheader("2 · Choose documents")
    @st.cache_data(ttl=60, show_spinner=False)
    def _account_docs(_n_processed: int):
        return rag.account_documents(pi)

    try:
        docs = _account_docs(len(ss.processed))
    except Exception:  # noqa: BLE001  fall back to the local registry
        docs = {}
    for v in rag.load_registry().values():   # include just-uploaded docs
        docs.setdefault(v["doc_id"], v)
    if not docs:
        st.info("Upload a PDF to get started.")
        st.stop()
    labels = {d: f"{v['name']}" + ("" if v.get("status") == "completed" else f" ({v.get('status')})")
              for d, v in docs.items()}
    selected = st.multiselect("Ask questions about", list(docs), default=list(docs)[:1],
                              format_func=lambda d: labels[d])

    st.subheader("3 · Answer engine")
    engine = st.radio("Engine", ["Groq (tree search + answer)", "PageIndex Chat API"],
                      help="Groq: your LLM reasons over the tree (shows sources & reasoning). "
                           "PageIndex Chat: hosted end-to-end answer, no LLM calls on your side.")
    model = st.selectbox("Groq model", rag.GROQ_MODELS, disabled=not engine.startswith("Groq"))
    with st.expander("Expert routing rules (optional)"):
        rules = st.text_area("Domain hints injected into retrieval",
                             placeholder="e.g. 'risk' questions → clauses 6.1.2/6.1.3 and 8.2/8.3\n"
                                         "specific controls → Annex A", height=140)

    c1, c2 = st.columns(2)
    if c1.button("🧹 Clear chat", use_container_width=True):
        ss.messages = []
        st.rerun()
    if c2.button("🗑️ Forget docs", use_container_width=True, disabled=not selected,
                 help="Remove selected docs from this app's list (and delete from PageIndex cloud)"):
        for d in selected:
            try:
                pi.delete_document(d)
            except Exception:  # noqa: BLE001
                pass
            rag.forget(d)
            ss.trees.pop(d, None)
        _account_docs.clear()
        st.rerun()

# ── Load trees for the selection ────────────────────────────────────────────
if not selected:
    st.info("Select at least one document in the sidebar.")
    st.stop()

trees = {}
for d in selected:
    if d not in ss.trees:
        try:
            ss.trees[d] = rag.get_tree(pi, d)
        except Exception as e:  # noqa: BLE001
            st.error(f"Couldn't load tree for {docs[d]['name']}: {e}")
            continue
    trees[d] = (docs[d]["name"], ss.trees[d])
forest = rag.build_forest(trees)

# ── Main area ───────────────────────────────────────────────────────────────
st.header("Ask your documents")
st.caption(" · ".join(f"📄 {name} ({rag.count_nodes(t)} sections)" for name, t in trees.values()))

with st.expander("🌲 Document structure"):
    for name, t in trees.values():
        st.markdown(f"**{name}**")
        st.code("\n".join(rag.tree_lines(t)), language=None)


def render_meta(meta: dict):
    if not meta:
        return
    if meta.get("nodes"):
        with st.expander(f"📚 Sources ({len(meta['nodes'])})"):
            for n in meta["nodes"]:
                doc = f"{n['doc_name']} · " if n.get("doc_name") and len(trees) > 1 else ""
                st.markdown(f"**{doc}{n['title']}** — p.{rag.pages(n)}  `[{n['node_id']}]`")
                snippet = (n.get("summary") or n.get("text") or "")[:400]
                if snippet:
                    st.caption(snippet + ("…" if len(snippet) == 400 else ""))
    if meta.get("thinking"):
        with st.expander("🧠 Retrieval reasoning"):
            st.write(meta["thinking"])


for m in ss.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        render_meta(m.get("meta"))

if not ss.messages:
    st.markdown("**Try:**")
    examples = ["Summarize the main topics of this document.",
                "What are the key requirements?",
                "Which section talks about risk, and what does it say?"]
    cols = st.columns(len(examples))
    for c, ex in zip(cols, examples):
        if c.button(ex, use_container_width=True):
            ss.pending = ex
            st.rerun()

question = st.chat_input("Ask a question about the selected document(s)…") or ss.pop("pending", None)

if question:
    history = [{"role": m["role"], "content": m["content"]} for m in ss.messages]
    ss.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            if engine.startswith("Groq"):
                with st.spinner("Reasoning over the document tree…"):
                    res = rag.answer(llm, model, question, forest, rules, history)
                meta = {"nodes": res["nodes"], "thinking": res["thinking"]}
                st.markdown(res["answer"])
                render_meta(meta)
                ss.messages.append({"role": "assistant", "content": res["answer"], "meta": meta})
            else:
                with st.spinner("Asking PageIndex Chat…"):
                    text = rag.pageindex_chat(pi, selected, history + [{"role": "user", "content": question}])
                st.markdown(text)
                ss.messages.append({"role": "assistant", "content": text})
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if "rate_limit" in msg or "429" in msg:
                st.warning("Groq rate limit hit (free tier ≈ 8k tokens/min). Wait ~30s and retry, "
                           "or switch to `openai/gpt-oss-20b` / the PageIndex Chat engine.")
            elif "504" in msg or "Gateway Time-out" in msg or "timed out" in msg.lower():
                st.warning("PageIndex timed out (server-side). Try again, or use the Groq engine.")
            else:
                st.error(f"Something went wrong: {e}")
            ss.messages.pop()  # drop the unanswered question

