# VectorlessRAG

> No vector database. No embedding. No preprocessing. Just concurrent LLM calls.

A new retrieval paradigm that replaces the entire vector RAG pipeline with massively parallel LLM calls. Instead of building indexes and hoping similarity approximates relevance, we let LLMs read everything — concurrently.

A few hundred lines of Python. One dependency (`aiohttp`).

## The Problem

Traditional vector RAG has a long pipeline:

```
Document → Chunking → Embedding → Vector DB → Similarity Search → LLM Answer
```

Each step introduces problems:
- **Chunking** destroys document structure and loses context
- **Embedding** maps text to a fixed semantic space — similarity ≠ relevance
- **Vector DB** (Milvus / Pinecone / Chroma) adds infrastructure complexity
- **Embedding model selection** directly affects recall, especially for domain-specific content
- The entire preprocessing pipeline adds latency, failure points, and maintenance burden

[PageIndex](https://github.com/VectifyAI/PageIndex) (21k+ stars) showed that vectorless RAG is viable — using LLM-generated hierarchical indexes to locate information with 98.7% accuracy on FinanceBench. But it assumes a single structured document (like an annual report).

Real-world scenarios are messier: multiple heterogeneous documents (contracts, invoices, chat logs, bank statements), some with no inherent structure, where answers are scattered across files.

## The Idea

What if we skip all preprocessing and just **ask the LLM to read everything**?

```
N document segments → N concurrent LLM calls → Filter relevant → Summarize
```

Three design principles:
- **Zero preprocessing** — no vectorization, no indexing, no classification. Upload and query instantly.
- **Full coverage** — every segment is checked. No top-K recall. No missed information.
- **Concurrency over intelligence** — replace retrieval algorithm sophistication with raw parallel throughput.

This turns the retrieval problem into a pure **concurrent I/O problem**.

## Architecture

```
                     User Question
                          |
                          v
               +--------------------+
               | 1. Query Rewrite   |  Strong model (1 call)
               |                    |  Clarify + expand synonyms
               +--------------------+
                          |
                          v
               +--------------------+
               |    Splitter        |  Pure code, no LLM
               |    docs/ -> N segs |  Configurable token window + overlap
               +--------------------+
                          |
           +---------+---------+---------+
           v         v         v         v
        +-----+  +-----+  +-----+  +-----+
        | LLM |  | LLM |  | LLM |  | LLM |   2. Retrieval
        |  2  |  |  2  |  |  2  |  |  2  |   Lightweight model
        +--+--+  +--+--+  +--+--+  +--+--+   N segments = N parallel calls
           |         |         |         |
           v         v         v         v
        relevant?  relevant?  relevant?  relevant?
           |                     |
           v                     v
          Filter: keep only relevant results
                          |
                          v
               +--------------------+
               | 3. Summarizer      |  Strong model (1 call, streaming)
               |                    |  Synthesize + cite sources
               +--------------------+  Detect contradictions
                          |
                          v
                    Final Answer
                    (with file + line references)
```

## Why It's Cheap: 3-Tier Model Strategy

The key insight: **retrieval judgment is a trivially simple task**. The LLM only needs to read a segment and output `{"relevant": true/false}`. This doesn't require a powerful model.

| Node | Task | Recommended | Calls per query |
|------|------|-------------|-----------------|
| **Query Rewrite** | Understand + expand question | Strong model | 1 |
| **Retrieval** | Judge relevance per segment | **Lightweight / mini model** | N |
| **Summarizer** | Synthesize final answer | Strong model | 1 |

The expensive calls (strong model) happen only **twice**. The N parallel calls use the cheapest, fastest model you have. This keeps total cost low even with dozens of segments.

> **Tip**: If your lightweight model supports a "thinking" or "reasoning" mode, disable it for retrieval. A simple true/false judgment doesn't need chain-of-thought, and disabling it significantly reduces latency.

## vs Vector RAG

```
                    Vector RAG                    VectorlessRAG
                    ----------                    -------------
Architecture:       Embedding + VectorDB + LLM    LLM only
Preprocessing:      Required (minutes)            None (zero)
Retrieval method:   Cosine similarity             LLM comprehension
Recall strategy:    Top-K nearest                 Full scan
Recall risk:        May miss (sim ≠ relevance)    No miss (full coverage)
Infrastructure:     VectorDB + Embedding service   Single LLM API endpoint
Explainability:     Chunk ID only                 File + line range
Setup time:         Hours (pipeline + tuning)      Minutes (config API keys)
```

## Quick Start

```bash
python3 -m pip install -r requirements.txt
```

Put at least one Markdown document in `docs/` before starting. The app only reads `.md` files, and it will exit if `docs/` is empty.

Example file:

```md
# Example

This is a sample document for VectorlessRAG.
```

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Then fill in `.env`:

```dotenv
# Strong model (query rewrite + summarization)
MAIN_API_KEY=your-main-api-key
MAIN_BASE_URL=https://api.example.com
MAIN_MODEL=your-strong-model

# Lightweight model (retrieval)
RETRIEVAL_API_KEY=your-retrieval-api-key
RETRIEVAL_BASE_URL=https://api.example.com
RETRIEVAL_MODEL=your-lightweight-model
RETRIEVAL_API_STYLE=auto

# Optional provider-specific retrieval parameters (must be valid JSON)
RETRIEVAL_EXTRA_BODY=

# Splitting
MAX_TOKENS=1000
OVERLAP_TOKENS=100
```

You can use the same model for all nodes, or mix providers. Retrieval defaults to `RETRIEVAL_API_STYLE=auto`: if the URL ends with `/responses`, it uses Responses API; otherwise it defaults to Chat Completions. If needed, you can still force `chat_completions` or `responses` manually. Extra provider-specific fields such as reasoning controls can be set via `RETRIEVAL_EXTRA_BODY`.

`start.py` will auto-install missing dependencies from `requirements.txt` on first launch and auto-load `.env` if it exists.
The app uses `certifi` for HTTPS certificate verification to avoid common local Python certificate issues on macOS.

```bash
# Put .md files in docs/
python start.py
# Or double-click start.bat on Windows / start.command on macOS
```

If startup says `No .md files found in ./docs`, add a file such as `docs/example.md` and launch again.

## Project Structure

```
vectorless-rag/
├── .env.example     Example local configuration
├── start.py         Cross-platform launcher
├── requirements.txt Python dependencies
├── main.py          Entry point, interactive loop
├── config.py        Reads runtime settings from environment variables
├── splitter.py      Document loading & token-based splitting
├── rewriter.py      Query rewrite (LLM node 1)
├── retriever.py     N-way concurrent retrieval (LLM node 2)
├── summarizer.py    Streaming summarization (LLM node 3)
├── logger.py        Markdown query logs with timing
├── start.bat        Windows double-click launcher
├── start.command    macOS double-click launcher
├── docs/            Your .md files here
└── logs/            Auto-generated query logs
```

## Limitations & Roadmap

| Current | Future |
|---------|--------|
| .md files only | PDF / DOCX parser |
| No caching | Result cache (question hash → results) |
| No rate limiting | Configurable semaphore |
| Summarizes from retrieval excerpts | Pass full original text of relevant segments |

## Best Suited For

- **Legal case analysis** — cross-referencing contracts, agreements, correspondence
- **Due diligence** — scanning document rooms for specific facts
- **Compliance review** — checking multiple policy documents
- **Research** — finding information across scattered notes and papers
- Any scenario where **recall matters more than per-query cost**, and document volume is bounded

## License

MIT
