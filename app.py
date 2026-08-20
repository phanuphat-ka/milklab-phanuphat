from __future__ import annotations

import logging
import os
import re
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import faiss
import numpy as np
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from streamlit.runtime import exists as streamlit_runtime_exists


ROOT_DIR = Path(__file__).resolve().parent
KB_PATH = ROOT_DIR / "guitar_kb.md"
EMBEDDING_MODEL_NAME = os.environ.get(
    "RAG_EMBEDDING_MODEL",
    "gemini-embedding-2",
)
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")


logger = logging.getLogger("milklab.rag")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


@dataclass(frozen=True)
class KBChunk:
    title: str
    text: str


def load_kb_text() -> str:
    return KB_PATH.read_text(encoding="utf-8")


def split_markdown_into_chunks(markdown_text: str) -> list[KBChunk]:
    chunks: list[KBChunk] = []
    current_title = "GuitarLab Knowledge Base"
    current_lines: list[str] = []

    def flush_chunk() -> None:
        nonlocal current_lines
        body = "\n".join(current_lines).strip()
        if body:
            chunks.append(KBChunk(title=current_title, text=body))
        current_lines = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        heading = re.match(r"^(#{2,6})\s+(.*)$", line.strip())
        if heading:
            flush_chunk()
            current_title = heading.group(2).strip()
            continue

        if line.startswith("# "):
            continue

        current_lines.append(line)

    flush_chunk()
    return chunks


@st.cache_resource(show_spinner=False)
def build_vector_store(
    kb_path_str: str,
    kb_mtime: float,
    embedding_model_name: str,
) -> dict[str, object]:
    del kb_mtime
    kb_text = Path(kb_path_str).read_text(encoding="utf-8")
    chunks = split_markdown_into_chunks(kb_text)
    chunk_texts = [chunk.text for chunk in chunks]

    if not chunk_texts:
        raise ValueError("Knowledge base is empty")

    api_key = load_api_key()
    if not api_key:
        raise ValueError("API key is required for building vector store")
    
    client = genai.Client(api_key=api_key)
    embeddings_list = []
    for text in chunk_texts:
        response = client.models.embed_content(
            model=embedding_model_name,
            contents=text,
        )
        embeddings_list.append(response.embeddings[0].values)
        
    embeddings = np.array(embeddings_list, dtype=np.float32)

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    return {
        "chunks": chunks,
        "index": index,
        "dimension": embeddings.shape[1],
    }


def load_api_key() -> str:
    load_dotenv(ROOT_DIR / ".env")
    return (
        os.environ.get("GOOGLE_API_KEY", "").strip()
        or os.environ.get("GEMINI_API_KEY", "").strip()
    )


@contextmanager
def trace_span(name: str, trace_id: str, **attrs: object):
    started_at = time.perf_counter()
    logger.info("start span=%s trace_id=%s attrs=%s", name, trace_id, attrs)
    try:
        yield
    except Exception:
        logger.exception("error span=%s trace_id=%s", name, trace_id)
        raise
    finally:
        elapsed_ms = (time.perf_counter() - started_at) * 1000.0
        logger.info(
            "end span=%s trace_id=%s elapsed_ms=%.2f attrs=%s",
            name,
            trace_id,
            elapsed_ms,
            attrs,
        )


def retrieve_top_k(
    query: str,
    *,
    trace_id: str,
    resources: dict[str, object],
    api_key: str,
    embedding_model_name: str,
    top_k: int = 3,
) -> list[dict[str, object]]:
    with trace_span("retrieve_top_k", trace_id, top_k=top_k, query=query):
        chunks = resources["chunks"]
        index = resources["index"]

        if not query.strip():
            return []

        assert isinstance(chunks, list)
        assert isinstance(index, faiss.Index)

        client = genai.Client(api_key=api_key)
        response = client.models.embed_content(
            model=embedding_model_name,
            contents=[query],
        )
        query_embedding = np.array([response.embeddings[0].values], dtype=np.float32)

        limit = min(top_k, len(chunks))
        scores, indices = index.search(query_embedding, limit)

        results: list[dict[str, object]] = []
        for score, index_position in zip(scores[0], indices[0]):
            if index_position < 0:
                continue
            chunk = chunks[index_position]
            if isinstance(chunk, dict):
                title = str(chunk.get("title", "Untitled"))
                text = str(chunk.get("text", ""))
            else:
                # Avoid strict isinstance(KBChunk) because cached objects from previous
                # Streamlit reloads may not share the same class identity.
                title = str(getattr(chunk, "title", "Untitled"))
                text = str(getattr(chunk, "text", ""))
            results.append(
                {
                    "title": title,
                    "text": text,
                    "score": float(score),
                }
            )

        return results


def build_prompt(query: str, retrieved_chunks: Iterable[dict[str, object]]) -> str:
    sources: list[str] = []
    for position, chunk in enumerate(retrieved_chunks, start=1):
        sources.append(
            f"[{position}] {chunk['title']} (score={chunk['score']:.3f})\n{chunk['text']}"
        )

    context_block = "\n\n".join(
        sources) if sources else "ไม่มีข้อมูลที่เกี่ยวข้อง"

    return f"""
คุณคือผู้ช่วยของ GuitarLab สำหรับตอบคำถามจากคลังความรู้ภายในร้านเท่านั้น
- ตอบเป็นภาษาไทย สุภาพ กระชับ และตรงคำถาม
- ใช้เฉพาะบริบทที่ให้มา ถ้าไม่มีข้อมูลเพียงพอให้บอกว่าไม่แน่ใจและขอข้อมูลเพิ่ม
- ถ้าผู้ใช้ถามเกินคลังความรู้ ให้ตอบอย่างตรงไปตรงมาว่าไม่มีข้อมูลในคลังความรู้นี้

คลังความรู้ที่ค้นคืนมา:
{context_block}

คำถามผู้ใช้:
{query}

คำตอบ:
""".strip()


def generate_answer(
    query: str,
    retrieved_chunks: list[dict[str, object]],
    *,
    trace_id: str,
    api_key: str,
    model_name: str,
) -> str:
    with trace_span(
        "generate_answer",
        trace_id,
        model=model_name,
        retrieved=len(retrieved_chunks),
    ):
        client = genai.Client(api_key=api_key)
        prompt = build_prompt(query, retrieved_chunks)
        
        last_error = None
        tried_models = []
        models_to_try = [model_name, "gemini-3.5-flash", "gemini-3.0-flash"]
        
        for current_model in models_to_try:
            if not current_model or current_model in tried_models:
                continue
            tried_models.append(current_model)
            
            try:
                response = client.models.generate_content(
                    model=current_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        system_instruction=(
                            "You are a Thai RAG chatbot for GuitarLab. Answer only from the provided context."
                        ),
                    ),
                )
                answer = (response.text or "").strip()
                return answer or "ขออภัย ฉันยังตอบคำถามนี้จากคลังความรู้ที่มีไม่ได้"
            except Exception as exc:
                last_error = exc
                error_text = str(exc)
                if "503" not in error_text and "UNAVAILABLE" not in error_text and "429" not in error_text and "RESOURCE_EXHAUSTED" not in error_text:
                    raise
                    
        raise last_error or Exception("All fallback models failed")


def render_chat_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "สวัสดีครับ มีอะไรให้ GuitarLab ช่วยไหมครับ ถามเรื่องสเปคกีต้าร์ ราคา หรือบริการเซ็ตอัพได้เลย",
            }
        ]


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --earth-ink: #3f2a1e;
            --earth-muted: #6f5645;
            --earth-sand: #f7efe3;
            --earth-cream: #fffaf3;
            --earth-clay: #c78c62;
            --earth-moss: #5d7358;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(199, 140, 98, 0.22), transparent 34%),
                radial-gradient(circle at top right, rgba(93, 115, 88, 0.16), transparent 26%),
                linear-gradient(180deg, #fbf3e8 0%, #fffdf9 46%, #f3eadc 100%);
            color: var(--earth-ink);
        }
        .hero {
            padding: 1.2rem 1.35rem;
            border-radius: 22px;
            border: 1px solid rgba(95, 67, 47, 0.12);
            background: linear-gradient(135deg, rgba(255, 250, 243, 0.9), rgba(247, 239, 227, 0.78));
            backdrop-filter: blur(10px);
            box-shadow: 0 18px 50px rgba(95, 67, 47, 0.08);
            margin-bottom: 1rem;
        }
        .hero h1 {
            margin: 0;
            font-size: 2.1rem;
            line-height: 1.1;
            color: var(--earth-ink);
        }
        .hero p {
            margin: 0.35rem 0 0;
            color: var(--earth-muted);
        }
        .stChatMessage {
            border-radius: 18px;
        }
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
            color: var(--earth-ink);
        }
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            background: rgba(199, 140, 98, 0.10);
            border: 1px solid rgba(199, 140, 98, 0.12);
        }
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
            background: rgba(93, 115, 88, 0.08);
            border: 1px solid rgba(93, 115, 88, 0.12);
        }
        .stChatInput textarea {
            background: rgba(255, 250, 243, 0.92) !important;
            color: var(--earth-ink) !important;
            border-color: rgba(95, 67, 47, 0.18) !important;
        }
        .stSidebar {
            background: linear-gradient(180deg, rgba(255, 250, 243, 0.98), rgba(242, 233, 220, 0.98));
            border-right: 1px solid rgba(95, 67, 47, 0.08);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> int:
    st.set_page_config(
        page_title="GuitarLab RAG Chatbot",
        page_icon="🎸",
        layout="wide",
    )
    apply_styles()
    init_session_state()

    st.markdown(
        """
        <div class="hero">
            <h1>GuitarLab RAG Chatbot</h1>
            <p>ถามข้อมูลจากคลังความรู้ร้าน แล้วระบบจะค้นจาก guitar_kb.md ก่อนตอบ</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.subheader("ข้อมูลระบบ")
        st.write(f"KB file: `{KB_PATH.name}`")
        st.write(f"Embedding model: `{EMBEDDING_MODEL_NAME}`")
        st.write(f"Gemini model: `{GEMINI_MODEL}`")

    kb_mtime = KB_PATH.stat().st_mtime
    resources = build_vector_store(
        str(KB_PATH), kb_mtime, EMBEDDING_MODEL_NAME)

    st.caption(
        f"Loaded {len(resources['chunks'])} chunks from {KB_PATH.name} with FAISS dim {resources['dimension']}"
    )

    render_chat_history()

    user_query = st.chat_input(
        "ถามเรื่องกีต้าร์ บริการซ่อม หรือราคา...")
    if not user_query:
        return 0

    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    trace_id = uuid.uuid4().hex[:10]
    st.session_state.last_trace_id = trace_id

    api_key = load_api_key()
    if not api_key:
        assistant_reply = (
            "ยังไม่ได้ตั้งค่า `GOOGLE_API_KEY` หรือ `GEMINI_API_KEY` ในไฟล์ .env"
        )
    else:
        retrieved_chunks = retrieve_top_k(
            user_query,
            trace_id=trace_id,
            resources=resources,
            api_key=api_key,
            embedding_model_name=EMBEDDING_MODEL_NAME,
            top_k=3,
        )

        with st.spinner("กำลังค้นข้อมูลและสร้างคำตอบ..."):
            try:
                assistant_reply = generate_answer(
                    user_query,
                    retrieved_chunks,
                    trace_id=trace_id,
                    api_key=api_key,
                    model_name=GEMINI_MODEL,
                )
            except Exception as exc:
                assistant_reply = f"เกิดข้อผิดพลาดระหว่างสร้างคำตอบ: {exc}"

    st.session_state.messages.append(
        {"role": "assistant", "content": assistant_reply})
    with st.chat_message("assistant"):
        st.markdown(assistant_reply)

    return 0


if __name__ == "__main__":
    if not streamlit_runtime_exists():
        os.execv(
            sys.executable,
            [sys.executable, "-m", "streamlit",
                "run", str(ROOT_DIR / "app.py")],
        )
    raise SystemExit(main())
