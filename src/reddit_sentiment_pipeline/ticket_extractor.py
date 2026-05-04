import re
import json
from pathlib import Path
from typing import List, Set
from rapidfuzz import fuzz, process
import spacy

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

class EnhancedTickerExtractor:
    def __init__(
        self,
        company_lookup_path: str | None = None,
        alias_path: str | None = None,
        fuzzy_threshold: int = 90,
    ):
        company_lookup_path = company_lookup_path or DATA_DIR / "ticker_lookup.json"
        alias_path = alias_path or DATA_DIR / "alias_lookup.json"

        with open(company_lookup_path, "r") as f:
            self.ticker_map = json.load(f)

        with open(alias_path, "r") as f:
            self.alias_map = json.load(f)

        self.company_map = {v.lower(): k for k, v in self.ticker_map.items()}
        for full_name in list(self.company_map.keys()):
            if "inc" in full_name:
                short_name = full_name.replace("inc.", "").strip()
                self.company_map[short_name] = self.company_map[full_name]
        self.fuzzy_threshold = fuzzy_threshold
        self.nlp = spacy.load("en_core_web_sm")

    def extract_from_text(self, text: str) -> List[str]:
        tickers = set()
        tickers.update(self._extract_dollar_tickers(text))
        tickers.update(self._match_company_names(text))
        tickers.update(self._match_named_entities(text))
        tickers.update(self._fuzzy_match(text))
        tickers.update(self._alias_match(text))
        return sorted(tickers)

    def _extract_dollar_tickers(self, text: str) -> Set[str]:
        matches = re.findall(r"\$([A-Za-z\-]{1,5})", text)
        return {m.upper() for m in matches if m.upper() in self.ticker_map}

    def _match_company_names(self, text: str) -> Set[str]:
        text_lower = text.lower()
        matched = set()
        for name, ticker in self.company_map.items():
            if len(name) < 3:
                continue
            if self._contains_phrase(text_lower, name):
                matched.add(ticker)
        return matched

    def _match_named_entities(self, text: str) -> Set[str]:
        doc = self.nlp(text)
        orgs = {ent.text.lower() for ent in doc.ents if ent.label_ == "ORG"}

        matched = set()
        for org in orgs:
            best_match = process.extractOne(org, self.company_map.keys(), scorer=fuzz.token_sort_ratio)
            if best_match and best_match[1] >= self.fuzzy_threshold:
                matched.add(self.company_map[best_match[0]])
        return matched

    def _fuzzy_match(self, text: str) -> Set[str]:
        matched = set()
        for candidate in self._candidate_phrases(text):
            best_match = process.extractOne(
                candidate.lower(),
                self.company_map.keys(),
                scorer=fuzz.token_sort_ratio,
            )
            if best_match and best_match[1] >= self.fuzzy_threshold:
                matched.add(self.company_map[best_match[0]])
        return matched

    def _alias_match(self, text: str) -> Set[str]:
        text_lower = text.lower()
        return {
            ticker
            for alias, ticker in self.alias_map.items()
            if len(alias) >= 3 and self._contains_phrase(text_lower, alias.lower())
        }

    def _candidate_phrases(self, text: str) -> Set[str]:
        doc = self.nlp(text)
        candidates = {
            ent.text.strip()
            for ent in doc.ents
            if ent.label_ in {"ORG", "PRODUCT", "PERSON"}
        }
        candidates.update(
            chunk.text.strip()
            for chunk in doc.noun_chunks
            if 1 <= len(chunk.text.split()) <= 4
        )
        candidates.update(
            match.strip()
            for match in re.findall(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3}\b", text)
        )
        return {candidate for candidate in candidates if len(candidate) >= 3}

    def _contains_phrase(self, text_lower: str, phrase_lower: str) -> bool:
        pattern = rf"(?<![A-Za-z0-9]){re.escape(phrase_lower)}(?![A-Za-z0-9])"
        return re.search(pattern, text_lower) is not None
    
if __name__ == "__main__":
    extractor = EnhancedTickerExtractor()
    sample_text = "I think $AAPL and Apple Inc. are going to do well. Also, check out tesla amazon nvidia google "
    tickers = extractor.extract_from_text(sample_text)
    print("Extracted Tickers:", tickers) 
