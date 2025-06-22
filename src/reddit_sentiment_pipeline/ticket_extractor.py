import re
import json
from typing import List, Set
from rapidfuzz import fuzz, process
import spacy

nlp = spacy.load("en_core_web_sm")

class EnhancedTickerExtractor:
    def __init__(self, company_lookup_path: str = "src/data/ticker_lookup.json", alias_path: str = "src/data/alias_lookup.json", fuzzy_threshold: int = 85):
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
        return {ticker for name, ticker in self.company_map.items() if name in text_lower}

    def _match_named_entities(self, text: str) -> Set[str]:
        doc = nlp(text)
        orgs = {ent.text.lower() for ent in doc.ents if ent.label_ == "ORG"}

        matched = set()
        for org in orgs:
            best_match = process.extractOne(org, self.company_map.keys(), scorer=fuzz.token_sort_ratio)
            if best_match and best_match[1] >= self.fuzzy_threshold:
                matched.add(self.company_map[best_match[0]])
        return matched

    def _fuzzy_match(self, text: str) -> Set[str]:
        results = process.extract(
            text.lower(), self.company_map.keys(), scorer=fuzz.token_sort_ratio
        )
        return {self.company_map[name] for name, score, _ in results if score >= self.fuzzy_threshold}

    def _alias_match(self, text: str) -> Set[str]:
        text_lower = text.lower()
        return {ticker for alias, ticker in self.alias_map.items() if alias in text_lower}
    
if __name__ == "__main__":
    extractor = EnhancedTickerExtractor()
    sample_text = "I think $AAPL and Apple Inc. are going to do well. Also, check out tesla amazon nvidia google "
    tickers = extractor.extract_from_text(sample_text)
    print("Extracted Tickers:", tickers) 
