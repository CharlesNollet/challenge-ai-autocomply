"""
Command line entry point for the minute book splitter.
"""

from __future__ import annotations

import argparse
import sys
import time

from solution.block_builder import BlockBuilder
from solution.config import (
    API_KEY,
    API_URL,
    BLOCK_SIZE,
    DEBUG_LOG_PATH,
    DEFAULT_MODEL,
    MAX_ITERATIONS,
    MAX_PARALLEL_REQUESTS,
)
from solution.debug_logger import DebugLogger
from solution.llm_client import LLMClient, LLMClientError
from solution.vision_client import VisionClient
from solution.minute_book_splitter import MinuteBookSplitter
from solution.page_classifier import PageClassifier
from solution.pdf_text_extractor import PDFTextExtractor
from solution.section_aggregator import SectionAggregator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minute book PDF splitter (AutoComply challenge).")
    parser.add_argument("pdf_path", help="Path to the PDF minute book.")
    parser.add_argument(
        "--output",
        "-o",
        default="result.json",
        help="Path to the output JSON file (default: result.json).",
    )
    parser.add_argument(
        "--block-size",
        type=int,
        default=BLOCK_SIZE,
        help=f"Number of target pages per block (default: {BLOCK_SIZE}).",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=MAX_ITERATIONS,
        help=f"Maximum classification passes (default: {MAX_ITERATIONS}).",
    )
    parser.add_argument(
        "--max-concurrent-requests",
        type=int,
        default=MAX_PARALLEL_REQUESTS,
        help=(
            "Upper bound on simultaneous API calls when classifying blocks "
            f"(default: {MAX_PARALLEL_REQUESTS})."
        ),
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"LLM model for /ask endpoint (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument("--api-url", default=API_URL, help="Override the API base URL.")
    parser.add_argument("--api-key", default=API_KEY, help="Override the API key.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    extractor = PDFTextExtractor()
    block_builder = BlockBuilder(block_size=args.block_size)
    debug_logger = DebugLogger(DEBUG_LOG_PATH)
    llm_client = LLMClient(api_url=args.api_url, api_key=args.api_key, model=args.model)
    vision_client = VisionClient(api_url=args.api_url, api_key=args.api_key, model=args.model)
    classifier = PageClassifier(
        block_builder=block_builder,
        llm_client=llm_client,
        vision_client=vision_client,
        max_iterations=args.max_iterations,
        max_parallel_requests=args.max_concurrent_requests,
        debug_logger=debug_logger,
    )
    aggregator = SectionAggregator()
    splitter = MinuteBookSplitter(
        extractor=extractor,
        block_builder=block_builder,
        llm_client=llm_client,
        classifier=classifier,
        aggregator=aggregator,
    )

    start_time = time.perf_counter()
    try:
        summary = splitter.run(args.pdf_path, args.output)
    except (FileNotFoundError, ValueError, LLMClientError) as exc:
        print(f"[ERROR] {exc}")
        return 1
    duration = time.perf_counter() - start_time

    print("Minute book classification complete.")
    print(f"Total pages: {summary['totalPages']}")
    print(f"Sections found: {len(summary['sections'])}")
    print(f"LLM requests: {summary['requests']}")
    print(f"Results written to: {args.output}")
    print(f"Elapsed time: {duration:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())


