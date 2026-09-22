"""Verify Phase 16: Tree-sitter Polyglot Support.

Iterates over sample test files in different languages and extracts
assertions and docstrings using the new PolyglotExtractor.
"""

import os
import logging

from orion.extraction.code_extractor import extract_assertions_from_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("Verifying Phase 16 Tree-sitter Polyglot Extractor...")
    
    sample_dir = os.path.join("tests", "polyglot", "sample_tests")
    if not os.path.exists(sample_dir):
        logger.error(f"Sample directory not found: {sample_dir}")
        return
        
    for filename in os.listdir(sample_dir):
        filepath = os.path.join(sample_dir, filename)
        if not os.path.isfile(filepath):
            continue
            
        logger.info(f"\nParsing {filename}...")
        with open(filepath, "r", encoding="utf-8") as f:
            source_code = f.read()
            
        results = extract_assertions_from_file(source_code, filename=filename)
        
        if not results:
            logger.warning(f"  No test functions found in {filename}!")
            continue
            
        for result in results:
            logger.info(f"  Function: {result.function_name}")
            logger.info(f"  Docstring: {result.docstring}")
            logger.info(f"  Fallback Used: {result.fallback_used}")
            logger.info(f"  Assertions Extracted: {len(result.assertions)}")
            
            for i, assertion in enumerate(result.assertions):
                logger.info(f"    [{i+1}] type={assertion.type}, op={assertion.operator}, left={assertion.left}, right={assertion.right}")
                
    logger.info("\nPhase 16 Verification Complete.")


if __name__ == "__main__":
    main()
