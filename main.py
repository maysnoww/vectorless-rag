import asyncio
import time
from splitter import load_and_split
from rewriter import rewrite_query
from retriever import retrieve_all
from summarizer import summarize
from logger import QueryLogger


def print_banner(segment_count, file_count):
    print()
    print("+--------------------------------------+")
    print("|  VectorlessRAG                       |")
    print(f"|  {file_count} files, {segment_count} segments{' ' * max(0, 18 - len(str(file_count)) - len(str(segment_count)))}|")
    print("|  Type your question, 'exit' to quit  |")
    print("+--------------------------------------+")
    print()


async def ask(segments, question, logger):
    """Full question-answering pipeline"""
    start = time.time()
    # Step 1: Query rewrite
    print("\n[REWRITE] Understanding question...")
    rewritten = await rewrite_query(question)
    if rewritten != question:
        print(f"  Rewritten: {rewritten}")
    else:
        print(f"  Using original question")
    # Step 2: Concurrent retrieval
    results = await retrieve_all(segments, rewritten, logger)
    # Step 3: Summarize
    answer = await summarize(results, question, logger)
    total_elapsed = time.time() - start
    print(f"\n[TIME] Total: {total_elapsed:.1f}s\n")
    return answer


def main():
    segments = load_and_split()
    if not segments:
        return

    logger = QueryLogger()
    print(f"[LOG] {logger.session_file}")

    files = set(s['file'] for s in segments)
    print_banner(len(segments), len(files))

    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not question:
            continue
        if question.lower() == 'exit':
            print("Bye!")
            break

        asyncio.run(ask(segments, question, logger))


if __name__ == '__main__':
    main()
