import os
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Union, Callable, Set

import spacy


def get_word_counts(text: str) -> list[tuple[str, int]]:
    words = text.lower().split()
    return Counter(words).most_common(20)


def remove_code_blocks(text: str) -> str:
    """Removes code blocks from a string.

    Args:
        text: The input string.

    Returns:
        The string with code blocks removed.
    """
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def remove_inline_code(text: str) -> str:
    """Removes inline code snippets from a string.

    Args:
        text: The input string.

    Returns:
        The string with inline code removed.
    """
    return re.sub(r"`[^`]*`", "", text)


def get_sentences(text: str) -> list[str]:
    """
    Returns a list of sentences from the given text.
    """
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    return [sentence.text for sentence in doc.sents]


def calculate_sentence_lengths(text: str) -> list[int]:
    """
    Calculates the length of each sentence in the given text.

    Args:
        text: The input text.

    Returns:
        A list of sentence lengths.
    """
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    return [len(sentence) for sentence in doc.sents]


def get_sentence_length_stats(text: str) -> dict[str, float]:
    """
    Calculates the min, max, average, and median sentence length of the given text.

    Args:
        text: The input text.

    Returns:
        A dictionary containing the min, max, average, and median sentence lengths.
    """
    text = remove_code_blocks(text)
    text = remove_inline_code(text)
    sentence_lengths = calculate_sentence_lengths(text)
    if not sentence_lengths:
        return {
            "min": 0.0,
            "max": 0.0,
            "average": 0.0,
            "median": 0.0,
        }
    min_length = min(sentence_lengths)
    max_length = max(sentence_lengths)
    average_length = sum(sentence_lengths) / len(sentence_lengths)
    sorted_lengths = sorted(sentence_lengths)
    median_length = (
        sorted_lengths[len(sorted_lengths) // 2]
        if len(sorted_lengths) % 2 != 0
        else (
            sorted_lengths[len(sorted_lengths) // 2 - 1]
            + sorted_lengths[len(sorted_lengths) // 2]
        )
        / 2
    )
    return {
        "min": float(min_length),
        "max": float(max_length),
        "average": average_length,
        "median": median_length,
    }


def count_words(
    text: str,
    exclude_stopwords: bool = True,
    exclude_punctuation: bool = True,
    exclude_digits: bool = False,
    min_word_length: int = 1,
    language_model: str = "en_core_web_sm",
) -> Dict[str, int]:
    """
    Count words in text, with options to filter out stopwords and other elements.

    Args:
        text: The input text to analyze
        exclude_stopwords: Whether to exclude common stopwords
        exclude_punctuation: Whether to exclude punctuation
        exclude_digits: Whether to exclude words containing digits
        min_word_length: Minimum word length to include in counts
        language_model: spaCy language model to use

    Returns:
        Dictionary with words as keys and their counts as values
    """
    # Remove code blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Remove newlines and backticks
    text = text.replace("\n", "").replace("`", "")

    # Load spaCy model
    nlp = spacy.load(language_model)

    # Process the text
    doc = nlp(text)

    # Filter words based on parameters
    filtered_words = []
    for token in doc:
        # Convert to lowercase
        word = token.text.lower()

        # Apply filters
        if exclude_stopwords and token.is_stop:
            continue
        if exclude_punctuation and token.is_punct:
            continue
        if exclude_digits and token.like_num:
            continue
        if len(word) < min_word_length:
            continue

        filtered_words.append(word)

    # Count word frequencies
    return dict(Counter(filtered_words).most_common(20))


def count_adjectives(
    text: str,
    exclude_stopwords: bool = True,
    exclude_punctuation: bool = True,
    exclude_digits: bool = False,
    min_word_length: int = 1,
    language_model: str = "en_core_web_sm",
) -> Dict[str, int]:
    """
    Count adjectives in text, with options to filter out stopwords and other elements.

    Args:
        text: The input text to analyze
        exclude_stopwords: Whether to exclude common stopwords
        exclude_punctuation: Whether to exclude punctuation
        exclude_digits: Whether to exclude words containing digits
        min_word_length: Minimum word length to include in counts
        language_model: spaCy language model to use

    Returns:
        Dictionary with adjectives as keys and their counts as values
    """
    text = remove_code_blocks(text)
    text = remove_inline_code(text)

    # Load spaCy model
    nlp = spacy.load(language_model)

    # Process the text
    doc = nlp(text)

    # Filter adjectives based on parameters
    filtered_adjectives = []
    for token in doc:
        # Apply filters

        if token.pos_ != "ADJ":
            continue

        word = token.text.lower()

        if exclude_stopwords and token.is_stop:
            continue
        if exclude_punctuation and token.is_punct:
            continue
        if exclude_digits and token.like_num:
            continue
        if len(word) < min_word_length:
            continue

        filtered_adjectives.append(word)

    # Count adjective frequencies
    return dict(Counter(filtered_adjectives).most_common(20))


def get_vale_config_path() -> str | None:
    return os.getenv("VALE_CONFIG_PATH")


def find_markdown_files(
    directory_path: Path, 
    include_pattern: str = "*.md", 
    exclude_patterns: List[str] = None
) -> List[Path]:
    """
    Find markdown files in a directory (and its subdirectories) that match the include pattern
    and don't match any of the exclude patterns.

    Args:
        directory_path: The path to the directory to search in.
        include_pattern: Glob pattern for files to include (default is "*.md").
        exclude_patterns: List of glob patterns for files to exclude.

    Returns:
        A list of file paths matching the criteria.
    """
    exclude_patterns = exclude_patterns or []
    
    # Ensure the directory exists
    if not directory_path.exists() or not directory_path.is_dir():
        raise ValueError(f"Directory does not exist or is not a directory: {directory_path}")
    
    # Find all files matching the include pattern
    all_files = list(directory_path.glob(f"**/{include_pattern}"))
    
    # Apply exclude patterns
    if exclude_patterns:
        excluded_files: Set[Path] = set()
        for pattern in exclude_patterns:
            excluded_files.update(directory_path.glob(f"**/{pattern}"))
        
        # Filter out excluded files
        return [f for f in all_files if f not in excluded_files]
    
    return all_files


def process_files_in_directory(
    directory_path: Path, 
    processor_func: Callable[[Path], str], 
    include_pattern: str = "*.md",
    exclude_patterns: List[str] = None,
    dry_run: bool = False
) -> Dict[Path, str]:
    """
    Process all matching files in a directory using the provided processor function.
    
    Args:
        directory_path: The path to the directory containing files to process.
        processor_func: A function that takes a file path and returns the processed content.
        include_pattern: Glob pattern for files to include (default is "*.md").
        exclude_patterns: List of glob patterns for files to exclude.
        dry_run: If True, files won't be modified, only return the processed content.
        
    Returns:
        A dictionary mapping file paths to their processed content.
    """
    files = find_markdown_files(directory_path, include_pattern, exclude_patterns)
    
    # Process each file
    results = {}
    for file_path in files:
        try:
            # Process the file
            processed_content = processor_func(file_path)
            results[file_path] = processed_content
            
            # Write the processed content back to the file if not in dry run mode
            if not dry_run and processed_content:
                with open(file_path, 'w') as f:
                    f.write(processed_content)
        except Exception as e:
            # Log the error and continue with the next file
            from loguru import logger
            logger.error(f"Error processing file {file_path}: {e}")
    
    return results