import re
import time
from dataclasses import dataclass
from .gemini import AIProviderError, MockGeminiProvider, get_ai_provider
from .retrieval import RetrieverService

INTENT_RULES = {
    "roadmap_stage_detail": ("roadmap_stage",),
    "lab_locator": ("nearby lab", "nearest lab", "lab near", "testing laboratory near", "पास की लैब", "नज़दीकी लैब"),
    "testing_guidance": ("lab test", "laboratory test", "which tests", "what tests", "testing required", "test required", "कौन से टेस्ट", "परीक्षण"),
    "manufacturing_roadmap": ("startup", "company", "manufactur", "factory", "making", "produce", "production", "launch a product", "make a product", "get this product", "business", "उत्पाद बनाना", "कंपनी", "स्टार्टअप", "निर्माण", "उत्पादन"),
    "verification": ("verify", "valid", "licence", "license", "registration", "जाँच", "वैध"),
    "application_guidance": ("apply", "application", "documents", "isi mark", "आवेदन", "दस्तावेज"),
    "complaint": ("complaint", "complain", "शिकायत"),
    "mark_explainer": ("hallmark", "mark mean", "चिह्न", "हॉलमार्क"),
    "standard_search": ("standard", "is code", "applies", "scope", "मानक"),
}

MANUFACTURING_ROADMAP = {
    "en": [
        "Define product use, ratings, capacity and materials",
        "Match the product against candidate standards and scope",
        "Prepare drawings, specifications, BOM and quality plan",
        "Confirm the applicable BIS certification scheme",
        "Arrange testing and compile technical evidence",
        "Prepare and submit the application documents",
        "Set up production inspection and compliance records",
    ],
    "hi": [
        "उत्पाद का उपयोग, रेटिंग, क्षमता और सामग्री तय करें",
        "उत्पाद को संभावित मानकों और उनके दायरे से मिलाएँ",
        "ड्रॉइंग, स्पेसिफिकेशन, BOM और गुणवत्ता योजना तैयार करें",
        "लागू BIS प्रमाणन योजना की पुष्टि करें",
        "परीक्षण करवाएँ और तकनीकी प्रमाण संकलित करें",
        "आवेदन दस्तावेज तैयार करके जमा करें",
        "उत्पादन निरीक्षण और अनुपालन रिकॉर्ड स्थापित करें",
    ],
}

def detect_intent(question: str) -> str:
    lowered = question.lower()
    for intent, needles in INTENT_RULES.items():
        if any(needle in lowered for needle in needles):
            return intent
    return "general_bis_help"

@dataclass
class RagResult:
    answer: str
    intent: str
    confidence: float
    citations: list
    next_steps: list[str]
    abstained: bool
    trace: dict

class RagAnswerService:
    def __init__(self, retriever=None, provider=None):
        self.retriever = retriever or RetrieverService()
        self.provider = provider or get_ai_provider()

    def answer(self, question: str, language="en") -> RagResult:
        started = time.monotonic()
        intent = detect_intent(question)
        retrieved = self.retriever.search(question, language=language)
        sensitive_terms = {"fee", "fees", "deadline", "timeline", "price", "शुल्क"}
        question_tokens = set(re.findall(r"[a-z0-9]+|[\u0900-\u097f]+", question.lower()))
        evidence_tokens = set(re.findall(r"[a-z0-9]+|[\u0900-\u097f]+", " ".join(item.chunk.text.lower() for item in retrieved)))
        if question_tokens & sensitive_terms and not evidence_tokens & sensitive_terms:
            retrieved = []
        evidence = [{"source_id": f"chunk:{x.chunk.id}", "standard_number": x.chunk.document.standard_number,
                     "title": x.chunk.document.title, "section": x.chunk.section, "page": x.chunk.page,
                     "text": x.chunk.text, "score": x.score} for x in retrieved]
        try:
            output = self.provider.generate(question=question, evidence=evidence, language=language, intent=intent)
            provider_error = None
        except AIProviderError as exc:
            output = MockGeminiProvider().generate(question=question, evidence=evidence, language=language, intent=intent)
            provider_error = str(exc)
        if not str(output.get("answer", "")).strip():
            output["answer"] = ("मुझे उपलब्ध स्रोतों में LED लैंप के लिए पर्याप्त प्रमाण नहीं मिला। कृपया कोई संबंधित मानक संख्या या अधिक उत्पाद विवरण दें।" if language == "hi" else
                                "I could not find enough evidence for LED lamps in the available demo corpus. Please provide a related standard number or more product details.")
            output["abstain"] = True
            output["confidence"] = 0
            output["citations"] = []
        allowed = {x["source_id"] for x in evidence}
        cited_ids = [x for x in output.get("citations", []) if x in allowed]
        citations = [x for x in retrieved if f"chunk:{x.chunk.id}" in cited_ids]
        if output.get("citations") and not citations:
            output = {"answer": "The generated answer could not be validated against retrieved evidence.", "confidence": 0, "citations": [], "abstain": True}
        generated_steps = [str(step).strip() for step in output.get("next_steps", []) if str(step).strip()][:8]
        roadmap = MANUFACTURING_ROADMAP.get(language, MANUFACTURING_ROADMAP["en"])
        if intent == "manufacturing_roadmap":
            # The roadmap is navigation, not free-form model output. Keep its
            # stage count and ordering stable even when the provider returns a
            # short or malformed next_steps array.
            generated_steps = roadmap.copy()
        if intent == "roadmap_stage_detail":
            stage_match = re.search(r"ROADMAP_STAGE\s+(\d+)\s+OF\s+(\d+)", question, re.I)
            current_stage = int(stage_match.group(1)) if stage_match else 1
            generated_steps = [] if current_stage >= len(roadmap) else [f"{current_stage + 1:02d}. {roadmap[current_stage]}"
            ]
        defaults = {"lab_locator": ["Share your city or 6-digit PIN code", "Search the official BIS LIMS laboratory directory"],
                 "testing_guidance": ["Confirm the exact test clauses from the complete standard", "Find a BIS-recognized laboratory with matching scope", "Prepare representative samples and technical documents"],
                 "standard_search": ["Open the standard summary", "Confirm applicability with BIS", "Start a certification checklist"],
                 "manufacturing_roadmap": ["Define the product and intended use", "Review candidate standards and scope", "Plan testing and technical documentation", "Confirm the applicable certification scheme with BIS", "Prepare the application and compliance controls"],
                 "application_guidance": ["Open the ISI certification guide", "Prepare the document checklist", "Confirm current details on the official BIS portal"],
                 "verification": ["Use the certification checker", "Confirm on the official BIS portal"]}
        steps = generated_steps if intent == "roadmap_stage_detail" else (generated_steps or defaults.get(intent, ["Ask a more specific follow-up", "Review cited sources"]))
        lab_results=[]
        if intent=="lab_locator" and re.search(r"maharashtra|441108|waranga|nagpur",question,re.I):
            lab_results=[{"name":"Anacon Laboratories Pvt. Ltd, Nagpur","location":"Butibori, Nagpur · 441122","valid_until":"15 Dec 2029","status":"Listed as BIS recognized","scope_status":"Verify exact IS scope","url":"https://lims.bis.gov.in/home/labs/"},{"name":"Electronics Regional Test Laboratory (West)","location":"Andheri East, Mumbai · 400093","valid_until":"31 Dec 2026","status":"Listed as BIS recognized","scope_status":"Verify exact IS scope","url":"https://lims.bis.gov.in/home/labs/"},{"name":"Kailtech Test and Research Centre Pvt. Ltd.","location":"Electronic Complex, Indore · 452010","valid_until":"18 Dec 2027","status":"Listed as BIS recognized","scope_status":"Verify exact IS scope","url":"https://lims.bis.gov.in/home/labs/"}]
        return RagResult(output["answer"], intent, float(output.get("confidence", 0)), citations, steps, bool(output.get("abstain")),
                         {"retrieved_source_ids": [x["source_id"] for x in evidence], "latency_ms": round((time.monotonic()-started)*1000), "provider": self.provider.__class__.__name__, "provider_error": provider_error, "lab_results": lab_results, "validation": "passed" if citations or output.get("abstain") else "failed"})
