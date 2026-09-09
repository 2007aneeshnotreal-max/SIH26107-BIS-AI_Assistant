from core.services.citations import CitationService
from core.services.embeddings import LocalEmbeddingService
from core.services.ingestion import IngestionService

def test_citation_validator_rejects_unretrieved_source():
    valid, complete=CitationService().validate(["chunk:1","chunk:99"],["chunk:1","chunk:2"])
    assert valid==["chunk:1"] and complete is False

def test_local_embedding_is_deterministic():
    service=LocalEmbeddingService()
    assert service.embed(["IS 367 kettle"])[0]==service.embed(["IS 367 kettle"])[0]
    assert len(service.embed(["standard"])[0])==128

def test_ingestion_rejects_unknown_mime_extension(tmp_path):
    path=tmp_path/"payload.exe";path.write_text("not allowed")
    try: IngestionService().validate(path)
    except ValueError as exc: assert "Unsupported" in str(exc)
    else: raise AssertionError("Unsafe extension was accepted")

