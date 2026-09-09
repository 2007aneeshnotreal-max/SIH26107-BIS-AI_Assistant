import csv, hashlib, json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from core.models import DocumentChunk, IngestionRun, SourceDocument
from core.services.chunking import chunk_text
from core.services.ingestion import IngestionService
from core.services.bis_dataset import normalize_record

class Command(BaseCommand):
    help = "Ingest controlled Markdown, text, JSON, JSONL or CSV sources."
    def add_arguments(self, parser):
        parser.add_argument("--path", required=True)
    def handle(self, *args, **options):
        root = Path(options["path"]).resolve()
        if not root.exists(): raise CommandError(f"Path does not exist: {root}")
        run = IngestionRun.objects.create(source_path=str(root), status="running")
        files = [root] if root.is_file() else [x for x in root.rglob("*") if x.suffix.lower() in {".pdf",".html",".htm",".md",".txt",".json",".jsonl",".csv"}]
        try:
            for path in files:
                if path.stat().st_size > 10 * 1024 * 1024: raise ValueError(f"File exceeds 10 MB: {path.name}")
                records = self.read_records(path)
                for idx, record in enumerate(records):
                    record = normalize_record(record)
                    content = str(record.get("content") or record.get("scope") or "")
                    document_id = str(record.get("document_id") or f"{path.stem}-{idx+1}")
                    if not content.strip():
                        raise ValueError(f"No searchable content in {document_id}")
                    checksum = hashlib.sha256(content.encode()).hexdigest()
                    with transaction.atomic():
                        doc, created = SourceDocument.objects.get_or_create(document_id=document_id, version=int(record.get("version",1)), defaults={"title":record.get("title",document_id), "standard_number":record.get("standard_number", ""), "content":content, "source_type":record.get("source_type","demo"), "source_url":record.get("source_url", ""), "language":record.get("language","en"), "category":record.get("category",""), "checksum":checksum})
                        if not created and doc.checksum != checksum:
                            raise ValueError(f"{document_id} already exists with different content; increment version")
                        if created:
                            passages = record.get("chunks")
                            if passages is None:
                                passages = [{"text":c.text, "section":c.section, "page":record.get("page") or c.page} for c in chunk_text(content)]
                            DocumentChunk.objects.bulk_create([
                                DocumentChunk(document=doc, chunk_index=i, section=c.get("section", ""), page=c.get("page"), text=c["text"], token_count=len(c["text"].split()), metadata=c.get("metadata", {}))
                                for i, c in enumerate(passages)
                            ])
                            run.chunks_created += len(passages)
                    run.documents_seen += 1
            run.status="complete"
        except Exception as exc:
            run.status="failed"; run.failed_records=[{"error":str(exc)}]; raise
        finally:
            run.finished_at=timezone.now(); run.save()
        self.stdout.write(self.style.SUCCESS(f"Ingested {run.documents_seen} documents / {run.chunks_created} chunks"))
    def read_records(self, path):
        if path.suffix.lower() in {".pdf", ".html", ".htm"}: return IngestionService().extract(path)
        if path.suffix == ".csv": return list(csv.DictReader(path.open(encoding="utf-8")))
        if path.suffix == ".json":
            data=json.loads(path.read_text(encoding="utf-8")); return data if isinstance(data,list) else [data]
        if path.suffix == ".jsonl": return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
        return [{"title":path.stem, "content":path.read_text(encoding="utf-8"), "source_type":"demo"}]
