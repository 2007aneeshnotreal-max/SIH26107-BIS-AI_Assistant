import math
import re
from difflib import SequenceMatcher
from dataclasses import dataclass
from functools import lru_cache
from core.models import DocumentChunk

STOP = {"the", "a", "an", "is", "are", "for", "of", "and", "to", "how", "what", "which", "does", "this", "in", "me", "i",
        "about", "tell", "supplied", "dataset", "say", "according", "please", "can", "you", "it"}

@lru_cache(maxsize=16000)
def terms(value: str) -> frozenset[str]:
    aliases = {"घरेलू":"domestic household", "प्रेशर":"pressure", "कुकर":"cooker", "केतली":"kettle",
               "मानक":"standard", "टूथपेस्ट":"toothpaste", "चप्पल":"slippers sandals", "कपड़े":"clothing"}
    expanded = value.lower()
    for source, target in aliases.items():
        expanded = expanded.replace(source, f" {target} ")
    return frozenset(x for x in re.findall(r"[a-z0-9]+", expanded) if len(x) > 1 and x not in STOP)

@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    score: float

class RetrieverService:
    """Deterministic local hybrid retriever; Qdrant adapter is a drop-in production extension."""
    def search(self, query: str, limit: int = 5, language: str = "en") -> list[RetrievedChunk]:
        query_terms = terms(query)
        demo_ids = set(re.findall(r"\bdemo-(?:is|rec|lic|cert|app|test|cmp)-[a-z]+-\d+(?::\d{4})?\b", query.lower()))
        exact_ids = set(re.findall(r"\bis(?:/iso)?\s+\d+(?:\s*\([^)]*\))?(?::\d{4})?", query.lower()))
        scored = []
        identifier_documents = set()
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
            identifier_boost = 3 if any(x in haystack.lower() for x in demo_ids) else 0
            if any(x in chunk.document.standard_number.lower() for x in exact_ids):
                identifier_boost += 3
            if identifier_boost:
                identifier_documents.add(chunk.document_id)
            title_terms=terms(chunk.document.title)
            fuzzy_title=sum(1 for query_term in query_terms-title_terms if len(query_term)>=5 and any(abs(len(query_term)-len(candidate))<=2 and SequenceMatcher(None,query_term,candidate).ratio()>=.78 for candidate in title_terms))
            title_boost = (len(query_terms & title_terms) + fuzzy_title * .5) * 0.12
            score = lexical + identifier_boost + title_boost
            if chunk.metadata.get("record_id"):
                # Prefer substantive passages over short catalogue/provenance fields.
                section = chunk.section.split()[0]
                desired = "download"
                if query_terms & {"licence", "license", "certificate", "application", "requirements", "testing", "status", "fee", "fees"}:
                    desired = "product_certification"
                if query_terms & {"complaint", "complain", "contact", "authenticity", "hallmark", "faq", "faqs"}:
                    desired = "consumer_information"
                if query_terms & {"committee", "secretary", "revision", "amendments", "department"}:
                    desired = "view"
                if section == desired and (overlap or identifier_boost):
                    score += .18
                if section in {"provenance", "standards_catalogue"}:
                    score -= .15
                if chunk.metadata.get("is_synthetic") and not demo_ids and not query_terms & {"demo", "synthetic", "prototype", "fictional"}:
                    score -= .20
            if score > 0:
                scored.append(RetrievedChunk(chunk, round(score, 4)))
        if demo_ids or exact_ids:
            scored = [item for item in scored if item.chunk.document_id in identifier_documents]
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
