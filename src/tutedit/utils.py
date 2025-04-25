import os
import re
from collections import Counter
from typing import Dict, List, Optional, Union

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
