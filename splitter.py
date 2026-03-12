import os
import re
import math
from config import DOCS_DIR, MAX_TOKENS, OVERLAP_TOKENS

_CN_RE = re.compile(r'[\u4e00-\u9fff]')


def estimate_tokens(text):
    """Estimate token count: ~1.5 tokens per CJK char, ~0.4 tokens per other char"""
    chinese_chars = len(_CN_RE.findall(text))
    other_chars = len(text) - chinese_chars
    estimated = chinese_chars * 1.5 + other_chars * 0.4
    if not text:
        return 0
    return max(1, math.ceil(estimated))


def load_and_split():
    """Load all .md files from docs/, split by token count, return segment list"""
    segments = []

    if not os.path.exists(DOCS_DIR):
        print(f"[ERR] Document folder not found: {DOCS_DIR}")
        print("      Create the folder and add at least one .md file before starting.")
        return segments

    md_files = [f for f in os.listdir(DOCS_DIR) if f.endswith('.md')]
    if not md_files:
        print(f"[ERR] No .md files found in {DOCS_DIR}")
        print("      Add at least one Markdown file to docs/ before asking questions.")
        print("      Example: docs/example.md")
        return segments

    for filename in sorted(md_files):
        filepath = os.path.join(DOCS_DIR, filename)
        for enc in ['utf-8', 'gbk', 'utf-8-sig', 'latin-1']:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    lines = f.readlines()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        full_text = ''.join(lines)
        total_tokens = estimate_tokens(full_text)
        total_lines = len(lines)

        if total_tokens <= MAX_TOKENS:
            segments.append({
                'file': filename,
                'segment': 'full',
                'line_range': f'L1-{total_lines}',
                'tokens': total_tokens,
                'content': full_text
            })
        else:
            chunks = _split_by_tokens(lines)
            for i, (chunk_lines, start_line, end_line, chunk_tokens) in enumerate(chunks, 1):
                segments.append({
                    'file': filename,
                    'segment': f'{i}/{len(chunks)}',
                    'line_range': f'L{start_line}-{end_line}',
                    'tokens': chunk_tokens,
                    'content': ''.join(chunk_lines)
                })

    total_tokens_all = sum(s['tokens'] for s in segments)
    print(f"[LOAD] {total_tokens_all} tokens, {len(segments)} segments")

    return segments


def _split_by_tokens(lines):
    """Split lines by token count with overlap. Returns [(chunk_lines, start, end, tokens), ...]"""
    line_tokens = [estimate_tokens(line) for line in lines]

    chunks = []
    start = 0
    total = len(lines)

    while start < total:
        chunk_lines = []
        chunk_tokens = 0
        end = start
        hit_oversized_boundary = False

        while end < total:
            if line_tokens[end] > MAX_TOKENS:
                if chunk_lines:
                    hit_oversized_boundary = True
                    break
                oversized_line = lines[end]
                oversized_chunks = _split_oversized_line(oversized_line, end + 1)
                chunks.extend(oversized_chunks)
                end += 1
                break
            if chunk_tokens + line_tokens[end] > MAX_TOKENS and chunk_lines:
                break
            chunk_lines.append(lines[end])
            chunk_tokens += line_tokens[end]
            end += 1

        if chunk_lines:
            chunks.append((chunk_lines, start + 1, end, chunk_tokens))

        if end >= total:
            break

        if hit_oversized_boundary:
            start = end
            continue

        overlap_tokens = 0
        overlap_start = end
        while overlap_start > start and overlap_tokens < OVERLAP_TOKENS:
            overlap_start -= 1
            overlap_tokens += line_tokens[overlap_start]

        start = max(overlap_start, start + 1)

    return chunks


def _split_oversized_line(line, line_number):
    """Split a single over-limit line into safe chunks while preserving line references."""
    if not line:
        return [([""], line_number, line_number, 0)]

    chunks = []
    start_idx = 0
    line_length = len(line)

    while start_idx < line_length:
        end_idx = start_idx + 1
        best_end = end_idx

        while end_idx <= line_length:
            token_count = estimate_tokens(line[start_idx:end_idx])
            if token_count > MAX_TOKENS:
                break
            best_end = end_idx
            end_idx += 1

        if best_end == start_idx:
            best_end = min(line_length, start_idx + 1)

        chunk_text = line[start_idx:best_end]
        chunks.append(([chunk_text], line_number, line_number, estimate_tokens(chunk_text)))

        if best_end >= line_length:
            break

        overlap_chars = _estimate_overlap_chars(line, best_end)
        start_idx = max(best_end - overlap_chars, start_idx + 1)

    return chunks


def _estimate_overlap_chars(line, end_idx):
    """Approximate char overlap for an oversized line based on token overlap budget."""
    overlap_chars = 0
    overlap_tokens = 0
    idx = end_idx

    while idx > 0 and overlap_tokens < OVERLAP_TOKENS:
        idx -= 1
        overlap_tokens += estimate_tokens(line[idx])
        overlap_chars += 1

    return overlap_chars
