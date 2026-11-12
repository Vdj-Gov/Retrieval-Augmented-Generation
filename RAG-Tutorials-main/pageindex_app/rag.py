"""
Core logic for the PageIndex + Groq document Q&A app.

Pipeline (same as the crash-course notebook):
  1. Upload PDF to PageIndex cloud  -> doc_id
  2. PageIndex builds a hierarchical tree index (no chunking, no vectors)
  3. Groq LLM reasons over the tree to pick relevant node_ids
  4. Retrieve those sections' text
  5. Groq LLM writes an answer citing section titles + page ranges
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Callable, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pageindex import PageIndexClient

APP_DIR = Path(__file__).resolve().parent
# .env lives next to the notebook (one level up); a local .env overrides it
load_dotenv(APP_DIR.parent / ".env")
load_dotenv(APP_DIR / ".env", override=True)

REGISTRY_PATH = APP_DIR / "documents.json"
UPLOAD_DIR = APP_DIR / "uploads"

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]

# Groq free tier allows ~8k tokens/minute, so keep prompts small.
MAX_CONTEXT_CHARS = 14000
MAX_NODES = 6


# ── Clients ─────────────────────────────────────────────────────────────────
def keys_status() -> dict:
    def ok(k):
        v = os.getenv(k)
        return bool(v) and not v.startswith("your_")
    return {"PAGEINDEX_API_KEY": ok("PAGEINDEX_API_KEY"), "GROQ_API_KEY": ok("GROQ_API_KEY")}


def get_pi_client() -> PageIndexClient:
    return PageIndexClient(api_key=os.getenv("PAGEINDEX_API_KEY"))


def get_llm_client() -> OpenAI:
    # Groq is OpenAI-compatible: reuse the OpenAI SDK with Groq's endpoint.
    return OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url=GROQ_BASE_URL, max_retries=6)


# ── Local registry (file hash -> doc_id) so the same PDF is never re-indexed ──
def load_registry() -> dict:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {}


def save_registry(reg: dict) -> None:
    REGISTRY_PATH.write_text(json.dumps(reg, indent=2), encoding="utf-8")


def file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def register(data: bytes, name: str, doc_id: str, status: str = "processing") -> None:
    reg = load_registry()
    reg[file_hash(data)] = {"doc_id": doc_id, "name": name, "status": status,
                            "uploaded_at": time.strftime("%Y-%m-%d %H:%M")}
    save_registry(reg)


def set_status(doc_id: str, status: str) -> None:
    reg = load_registry()
    for v in reg.values():
        if v["doc_id"] == doc_id:
            v["status"] = status
    save_registry(reg)


def forget(doc_id: str) -> None:
    reg = {h: v for h, v in load_registry().items() if v["doc_id"] != doc_id}
    save_registry(reg)


def account_documents(pi: PageIndexClient, max_docs: int = 200) -> dict:
    """
    All documents in the PageIndex account: {doc_id: {"name", "status"}}.
    This is the source of truth for the doc list, so it survives restarts on
    hosts with an ephemeral filesystem (e.g. Streamlit Community Cloud).
    """
    docs, offset = {}, 0
    while offset < max_docs:
        page = pi.list_documents(limit=50, offset=offset)
        items = page.get("documents", [])
        for d in items:
            docs[d["id"]] = {"doc_id": d["id"], "name": d.get("name", d["id"]),
                             "status": d.get("status", "unknown")}
        offset += len(items)
        if not items or offset >= page.get("total", 0):
            break
    return docs


# ── Upload + indexing ───────────────────────────────────────────────────────
def upload_pdf(pi: PageIndexClient, data: bytes, name: str) -> tuple[str, bool]:
    """Returns (doc_id, reused). Re-uses an existing doc_id if this exact file was seen."""
    existing = load_registry().get(file_hash(data))
    if existing:
        return existing["doc_id"], True
    UPLOAD_DIR.mkdir(exist_ok=True)
    path = UPLOAD_DIR / name
    path.write_bytes(data)
    doc_id = pi.submit_document(str(path))["doc_id"]
    register(data, name, doc_id)
    return doc_id, False


def wait_until_ready(pi: PageIndexClient, doc_id: str,
                     on_status: Optional[Callable[[str], None]] = None,
                     timeout_s: int = 900) -> str:
    start = time.time()
    while True:
        status = pi.get_document(doc_id).get("status", "unknown")
        if on_status:
            on_status(status)
        if status in ("completed", "failed"):
            set_status(doc_id, status)
            return status
        if time.time() - start > timeout_s:
            return status
        time.sleep(4)


def get_tree(pi: PageIndexClient, doc_id: str) -> list:
    res = pi.get_tree(doc_id, node_summary=True)
    return res.get("result", []) if isinstance(res, dict) else res


# ── Tree helpers ────────────────────────────────────────────────────────────
def pages(n: dict) -> str:
    if n.get("start_index"):
        s, e = n["start_index"], n.get("end_index", n["start_index"])
        return f"{s}" if s == e else f"{s}-{e}"
    return str(n.get("page_index", "?"))


def count_nodes(nodes: list) -> int:
    return sum(1 + count_nodes(n.get("nodes", [])) for n in nodes)


def tree_lines(nodes: list, indent: int = 0) -> list[str]:
    out = []
    for n in nodes:
        out.append(f"{'    ' * indent}[{n['node_id']}] {n['title']}  (p.{pages(n)})")
        out += tree_lines(n.get("nodes", []), indent + 1)
    return out


def build_forest(trees: dict[str, tuple[str, list]]) -> list:
    """
    Merge several documents into one tree so a single tree search can span them.
    trees: {doc_id: (doc_name, tree)}. Node ids become "<k>-<node_id>".
    """
    forest = []
    for k, (doc_id, (name, tree)) in enumerate(trees.items(), start=1):
        t = copy.deepcopy(tree)

        def reid(nodes):
            for n in nodes:
                n["node_id"] = f"{k}-{n['node_id']}"
                n["doc_name"] = name
                reid(n.get("nodes", []))
        reid(t)
        if len(trees) == 1:
            return t
        forest.append({"node_id": f"{k}", "title": f"DOCUMENT: {name}", "doc_name": name, "nodes": t})
    return forest


def find_nodes(tree: list, ids: list) -> list:
    found = []
    for n in tree:
        if n["node_id"] in ids:
            found.append(n)
        found += find_nodes(n.get("nodes", []), ids)
    return found


def _compress(nodes: list) -> list:
    out = []
    for n in nodes:
        e = {"node_id": n["node_id"], "title": n["title"], "pages": pages(n),
             "summary": (n.get("summary") or n.get("text") or "")[:150]}
        if n.get("nodes"):
            e["children"] = _compress(n["nodes"])
        out.append(e)
    return out


# ── LLM steps ───────────────────────────────────────────────────────────────
def tree_search(llm: OpenAI, model: str, query: str, tree: list,
                expert_rules: str = "", history: list | None = None) -> dict:
    convo = ""
    if history:
        recent = history[-4:]
        convo = "Recent conversation (for resolving follow-ups):\n" + "\n".join(
            f"{m['role']}: {m['content'][:300]}" for m in recent) + "\n\n"
    rules = f"\nExpert routing rules (follow these):\n{expert_rules}\n" if expert_rules.strip() else ""
    prompt = f"""You are given a query and the tree structure of one or more documents (like a Table of Contents).
Identify the node IDs whose sections most likely contain the answer. Prefer the most specific
(deepest) nodes; pick at most {MAX_NODES}. Never pick a "Contents" / table-of-contents node.
{convo}Query: {query}

Document Tree:
{json.dumps(_compress(tree), separators=(",", ":"))}
{rules}
Reply ONLY in this JSON format:
{{"thinking": "<step-by-step reasoning>", "node_list": ["node_id1", "node_id2"]}}"""
    r = llm.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}],
                                    response_format={"type": "json_object"})
    try:
        return json.loads(r.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        return {"thinking": "Could not parse model output.", "node_list": []}


def generate_answer(llm: OpenAI, model: str, query: str, nodes: list,
                    history: list | None = None) -> str:
    if not nodes:
        return "⚠️ I couldn't find a relevant section in the selected document(s)."
    nodes = nodes[:MAX_NODES]
    per_node = max(1500, MAX_CONTEXT_CHARS // len(nodes))
    parts = []
    for n in nodes:
        doc = f"{n['doc_name']} | " if n.get("doc_name") else ""
        body = (n.get("text") or n.get("summary") or "")[:per_node]
        parts.append(f"[{doc}Section: '{n['title']}' | Pages {pages(n)}]\n{body}")
    context = "\n\n---\n\n".join(parts)
    msgs = [{"role": "system", "content":
             "You are an expert document analyst. Answer using ONLY the provided context. "
             "Cite the section title and page range in parentheses for every claim, e.g. "
             "(5 Leadership, p.8-9). If the context doesn't contain the answer, say so. "
             "Use markdown; be concise and precise."}]
    for m in (history or [])[-4:]:
        msgs.append({"role": m["role"], "content": m["content"][:1000]})
    msgs.append({"role": "user", "content": f"Question: {query}\n\nContext:\n{context}"})
    r = llm.chat.completions.create(model=model, messages=msgs)
    return r.choices[0].message.content


def answer(llm: OpenAI, model: str, query: str, tree: list,
           expert_rules: str = "", history: list | None = None) -> dict:
    search = tree_search(llm, model, query, tree, expert_rules, history)
    ids = [str(i) for i in search.get("node_list", [])]
    nodes = find_nodes(tree, ids)
    text = generate_answer(llm, model, query, nodes, history)
    return {"answer": text, "thinking": search.get("thinking", ""), "node_ids": ids, "nodes": nodes}


def pageindex_chat(pi: PageIndexClient, doc_ids: list[str], history: list) -> str:
    """PageIndex's hosted Chat API — PageIndex runs retrieval + LLM itself."""
    msgs = [{"role": m["role"], "content": m["content"]} for m in history]
    target = doc_ids if len(doc_ids) > 1 else doc_ids[0]
    text = ""
    for turns in (None, 12):
        kw = {"max_turns": turns} if turns else {}
        r = pi.chat_completions(messages=msgs, doc_id=target, **kw)
        text = (r["choices"][0]["message"]["content"] or "").strip()
        # occasionally the hosted agent returns an unexecuted tool call — retry once
        if text and "<invoke" not in text and "<parameter" not in text:
            return text
    return text or "⚠️ PageIndex Chat returned no answer — try again or use the Groq engine."

