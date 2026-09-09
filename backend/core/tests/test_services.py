from core.services.chunking import chunk_text
from core.services.rag import detect_intent
from core.services.gemini import MockGeminiProvider
from core.services.rag import RagAnswerService
from django.core.management import call_command
from core.services.retrieval import RetrieverService

def test_chunk_preserves_identifier():
    chunks=chunk_text(("1 SCOPE\nIS 302 (Part 2/Sec 24):1994 applies to refrigerators. ")*80,target_words=100)
    assert chunks and "IS 302" in chunks[0].text

def test_intent_routing():
    assert detect_intent("ROADMAP_STAGE 02 OF 07") == "roadmap_stage_detail"
    assert detect_intent("Which lab tests are required?") == "testing_guidance"
    assert detect_intent("Recommend a nearby lab") == "lab_locator"
    assert detect_intent("How do I verify a licence?")=="verification"
    assert detect_intent("What documents do I need to apply?")=="application_guidance"
    assert detect_intent("I run a startup and want to manufacture electric kettles")=="manufacturing_roadmap"
    assert detect_intent("I will be making kettles which certification is required to get this product into production")=="manufacturing_roadmap"
    assert detect_intent("मैं कंपनी में उत्पाद बनाना चाहता हूं")=="manufacturing_roadmap"

def test_roadmap_stage_always_has_the_following_number(db):
    call_command("seed_demo_data",verbosity=0)
    result=RagAnswerService(provider=MockGeminiProvider()).answer("ROADMAP_STAGE 02 OF 07\nSTAGE_TITLE: Review standards\nPRODUCT_CONTEXT: electric kettle")
    assert result.intent == "roadmap_stage_detail"
    assert result.next_steps[0].startswith("03.")
    completed=RagAnswerService(provider=MockGeminiProvider()).answer("ROADMAP_STAGE 07 OF 07\nSTAGE_TITLE: Production compliance\nPRODUCT_CONTEXT: electric kettle")
    assert completed.next_steps == []

def test_manufacturing_roadmap_always_has_all_seven_stages(db):
    class ShortRoadmapProvider:
        def generate(self, **kwargs):
            source_id = kwargs["evidence"][0]["source_id"]
            return {"answer": "A short provider answer.", "confidence": 0.8,
                    "citations": [source_id], "next_steps": ["First", "Second"],
                    "abstain": False}

    call_command("seed_demo_data", verbosity=0)
    result = RagAnswerService(provider=ShortRoadmapProvider()).answer(
        "I want to manufacture electric kettles. Give me a roadmap."
    )

    assert result.intent == "manufacturing_roadmap"
    assert len(result.next_steps) == 7
    assert result.next_steps[0].startswith("Define product")
    assert result.next_steps[-1].startswith("Set up production")

def test_retrieval_tolerates_small_product_typos(db):
    call_command("seed_demo_data",verbosity=0)
    results=RetrieverService().search("microwace")
    assert results
    assert results[0].chunk.document.standard_number == "IS 11676:1995"
