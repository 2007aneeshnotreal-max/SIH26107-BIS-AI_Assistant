import csv, hashlib, json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.models import DocumentChunk, IngestionRun, SourceDocument
from core.services.chunking import chunk_text
from core.services.ingestion import IngestionService

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
                    content = str(record.get("content") or record.get("scope") or "")
                    document_id = str(record.get("document_id") or f"{path.stem}-{idx+1}")
                    doc, _ = SourceDocument.objects.update_or_create(document_id=document_id, version=int(record.get("version",1)), defaults={"title":record.get("title",document_id), "standard_number":record.get("standard_number", ""), "content":content, "source_type":record.get("source_type","demo"), "source_url":record.get("source_url", ""), "language":record.get("language","en"), "category":record.get("category",""), "checksum":hashlib.sha256(content.encode()).hexdigest()})
                    DocumentChunk.objects.filter(document=doc).delete()
                    for chunk in chunk_text(content): DocumentChunk.objects.create(document=doc, chunk_index=chunk.index, section=chunk.section, page=record.get("page") or chunk.page, text=chunk.text, token_count=len(chunk.text.split()))
                    run.documents_seen += 1; run.chunks_created += doc.chunks.count()
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
