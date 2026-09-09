import math
import re
from difflib import SequenceMatcher
from dataclasses import dataclass
from core.models import DocumentChunk

STOP = {"the", "a", "an", "is", "are", "for", "of", "and", "to", "how", "what", "which", "does", "this", "in", "me", "i"}

def terms(value: str) -> set[str]:
    aliases = {"घरेलू":"domestic household", "प्रेशर":"pressure", "कुकर":"cooker", "केतली":"kettle",
               "मानक":"standard", "टूथपेस्ट":"toothpaste", "चप्पल":"slippers sandals", "कपड़े":"clothing"}
    expanded = value.lower()
    for source, target in aliases.items():
        expanded = expanded.replace(source, f" {target} ")
    return {x for x in re.findall(r"[a-z0-9]+", expanded) if len(x) > 1 and x not in STOP}

@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    score: float

class RetrieverService:
    """Deterministic local hybrid retriever; Qdrant adapter is a drop-in production extension."""
    def search(self, query: str, limit: int = 5, language: str = "en") -> list[RetrievedChunk]:
        query_terms = terms(query)
        exact_ids = set(re.findall(r"(?:is(?:/iso)?\s*)?\d+(?:\s*\([^)]*\))?(?::\d{4})?", query.lower()))
        scored = []
        for chunk in DocumentChunk.objects.select_related("document").filter(document__is_active=True):
            haystack = f"{chunk.document.standard_number} {chunk.document.title} {chunk.section} {chunk.text}"
            hay_terms = terms(haystack)
            overlap = len(query_terms & hay_terms)
            fuzzy_matches = 0
            for query_term in query_terms - hay_terms:
                if len(query_term) < 5:
                    continue
                if any(abs(len(query_term)-len(candidate)) <= 2 and SequenceMatcher(None, query_term, candidate).ratio() >= .78 for candidate in hay_terms):
                    fuzzy_matches += 1
            lexical = (overlap + fuzzy_matches * .82) / math.sqrt(max(len(query_terms), 1) * max(len(hay_terms), 1))
            identifier_boost = 0.8 if any(x.strip() in haystack.lower() for x in exact_ids) else 0
            title_terms=terms(chunk.document.title)
            fuzzy_title=sum(1 for query_term in query_terms-title_terms if len(query_term)>=5 and any(abs(len(query_term)-len(candidate))<=2 and SequenceMatcher(None,query_term,candidate).ratio()>=.78 for candidate in title_terms))
            title_boost = (len(query_terms & title_terms) + fuzzy_title * .85) * 0.12
            score = lexical + identifier_boost + title_boost
            if score > 0:
                scored.append(RetrievedChunk(chunk, round(score, 4)))
        scored.sort(key=lambda item: item.score, reverse=True)
        seen, result = set(), []
        for item in scored:
            key = (item.chunk.document_id, item.chunk.section)
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
            if len(result) == limit:
                break
        return result
