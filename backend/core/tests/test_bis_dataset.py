import json
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command

from core.models import Citation, ChatMessage, ChatSession, DocumentChunk, SourceDocument
from core.services.bis_dataset import normalize_record
from core.services.gemini import MockGeminiProvider
from core.services.rag import RagAnswerService
from core.services.retrieval import RetrieverService


@pytest.fixture
def dataset():
    source = Path(__file__).resolve().parents[3] / 'data/sources/BIS_Prototype_and_Reference_521_Records.jsonl'
    return [json.loads(line) for line in source.read_text().splitlines() if line.strip()]


def test_all_records_preserve_provenance_and_searchable_content(dataset):
    normalized = [normalize_record(record) for record in dataset]
    assert len(normalized) == 521
    assert sum(record['source_type'] == 'demo' for record in normalized) == 500
    assert sum(record['source_type'] == 'user' for record in normalized) == 21
    for raw, record in zip(dataset, normalized):
        assert json.loads(record['content']) == raw
        assert record['chunks']
        assert len(record['title']) <= 500
        for chunk in record['chunks']:
            assert chunk['metadata']['is_synthetic'] is raw['is_synthetic']
            assert raw['product_name'] in chunk['text']
            assert len(chunk['text'].split()) < 280


def test_import_is_repeatable_and_preserves_citations(db, dataset, tmp_path):
    source = tmp_path / 'records.jsonl'
    source.write_text('\n'.join(json.dumps(row) for row in [dataset[0], dataset[500]]))
    call_command('ingest_sources', path=str(source), stdout=StringIO())
    ids = list(DocumentChunk.objects.values_list('id', flat=True))
    message = ChatMessage.objects.create(session=ChatSession.objects.create(), role='assistant', content='Fixture')
    Citation.objects.create(message=message, chunk_id=ids[0], label='Source', ordinal=1)
    call_command('ingest_sources', path=str(source), stdout=StringIO())
    assert list(DocumentChunk.objects.values_list('id', flat=True)) == ids
    assert SourceDocument.objects.count() == 2
    changed = dict(dataset[0], product_name='Changed fixture')
    source.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='increment version'):
        call_command('ingest_sources', path=str(source), stdout=StringIO())
    assert SourceDocument.objects.get(document_id=dataset[0]['record_id']).title.startswith('Rice flour')


def test_dataset_retrieval_and_synthetic_answer(db, dataset, tmp_path):
    source = tmp_path / 'records.jsonl'
    source.write_text('\n'.join(json.dumps(row) for row in [dataset[0], dataset[1], dataset[520]]))
    call_command('ingest_sources', path=str(source), stdout=StringIO())
    matches = RetrieverService().search('What is the licence status for DEMO-LIC-FOD-001?')
    assert matches[0].chunk.document.document_id == 'DEMO-REC-FOD-001'
    assert matches[0].chunk.section.startswith('product_certification')
    assert all(item.chunk.document.document_id == 'DEMO-REC-FOD-001' for item in matches)
    assert RetrieverService().search('DEMO-LIC-FOD-999') == []
    result = RagAnswerService(provider=MockGeminiProvider()).answer('Rice flour')
    assert 'supplied synthetic dataset' in result.answer
    assert result.answer.startswith('Rice flour')
    assert 'Prototype record:' not in result.answer
    assert 'DEMO-IS-' not in result.answer
    assert result.citations[0].chunk.document.document_id == 'DEMO-REC-FOD-001'
    licence = RagAnswerService(provider=MockGeminiProvider()).answer('What is the licence status for DEMO-LIC-FOD-001?')
    assert 'Status: Active' in licence.answer
    assert 'Holder: Demo Food Manufacturer 001' in licence.answer
    assert 'product_certification.' not in licence.answer
    reference = RetrieverService().search('IS 3024:2015')
    assert reference[0].chunk.document.document_id == 'REF-BIS-021'
    summary = RagAnswerService(provider=MockGeminiProvider()).answer('IS 3024:2015')
    assert 'transformer cores' in summary.answer
    assert 'not newly revalidated' in summary.answer
