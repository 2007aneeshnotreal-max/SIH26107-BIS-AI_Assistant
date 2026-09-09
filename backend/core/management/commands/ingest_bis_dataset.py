import csv
import json
import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import DocumentChunk, IngestionRun, SourceDocument, StandardRecord
from core.services.chunking import chunk_text


DATASET_VERSION = "BIS India RAG Dataset v2.0.0"


def flatten_value(value, prefix=""):
    if isinstance(value, dict):
        parts = []
        for key, child in value.items():
            child_prefix = f"{prefix} / {key}" if prefix else str(key)
            parts.extend(flatten_value(child, child_prefix))
        return parts
    if isinstance(value, list):
        parts = []
        for index, child in enumerate(value, 1):
            parts.extend(flatten_value(child, f"{prefix} [{index}]"))
        return parts
    if value is None or value == "":
        return []
    return [f"{prefix}: {value}"]


def record_content(record):
    lines = [
        f"Dataset: {DATASET_VERSION}",
        "This is user-provided BIS/RAG dataset material. Do not treat it as an official BIS decision.",
    ]
    lines.extend(flatten_value(record))
    return "\n".join(lines)


def source_content(chunk, registry_entry=None):
    lines = [
        f"Dataset: {DATASET_VERSION}",
        "This is user-provided source material. Verify current legal and regulatory claims against official sources.",
        f"Source ID: {chunk.get('source_id', '')}",
        f"Page: {chunk.get('page', '')}",
        f"Chunk: {chunk.get('chunk_index', '')}",
    ]
    if registry_entry:
        lines.extend(flatten_value(registry_entry, "Source registry"))
    lines.append(str(chunk.get("text", "")))
    return "\n".join(line for line in lines if line)


class Command(BaseCommand):
    help = "Ingest the supplied BIS RAG dataset ZIP as labelled retrieval evidence."

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True, help="Path to data.zip")

    @transaction.atomic
    def handle(self, *args, **options):
        archive_path = Path(options["path"]).expanduser().resolve()
        if not archive_path.is_file() or archive_path.suffix.lower() != ".zip":
            raise CommandError("--path must point to a ZIP archive")

        run = IngestionRun.objects.create(source_path=str(archive_path), status="running")
        documents_seen = 0
        chunks_created = 0
        try:
            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())
                required = {"product_regulatory_records_1088.jsonl", "source_chunks.jsonl"}
                missing = required - names
                if missing:
                    raise CommandError(f"Dataset is missing: {', '.join(sorted(missing))}")

                registry = {}
                if "source_registry.jsonl" in names:
                    for row in self.read_jsonl(archive, "source_registry.jsonl"):
                        registry[row.get("source_id", "")] = row

                for record in self.read_jsonl(archive, "product_regulatory_records_1088.jsonl"):
                    record_id = str(record.get("record_id") or record.get("serial_no") or documents_seen + 1)
                    standard = record.get("is_number_source_list") or ""
                    title = record.get("product_title_canonical") or record_id
                    content = record_content(record)
                    document, _ = SourceDocument.objects.update_or_create(
                        document_id=f"BIS-RAG-{record_id}",
                        version=1,
                        defaults={
                            "title": title[:500],
                            "standard_number": str(standard)[:120],
                            "source_type": SourceDocument.SourceType.USER,
                            "source_url": "",
                            "language": "en",
                            "category": str(record.get("sector", ""))[:100],
                            "content": content,
                            "checksum": "",
                        },
                    )
                    document.chunks.all().delete()
                    for item in chunk_text(content):
                        DocumentChunk.objects.create(
                            document=document,
                            chunk_index=item.index,
                            section=item.section or "Dataset record",
                            page=item.page,
                            text=item.text,
                            token_count=len(item.text.split()),
                            metadata={"dataset": DATASET_VERSION, "record_id": record_id},
                        )
                        chunks_created += 1
                    self.upsert_standard(record, document, title, standard)
                    documents_seen += 1

                for chunk in self.read_jsonl(archive, "source_chunks.jsonl"):
                    source_id = str(chunk.get("source_id") or chunk.get("chunk_id") or "unknown")
                    document, _ = SourceDocument.objects.update_or_create(
                        document_id=f"BIS-SOURCE-{source_id}",
                        version=1,
                        defaults={
                            "title": str(registry.get(source_id, {}).get("filename") or source_id)[:500],
                            "source_type": SourceDocument.SourceType.USER,
                            "source_url": "",
                            "language": "en",
                            "content": source_content(chunk, registry.get(source_id)),
                        },
                    )
                    chunk_index = int(chunk.get("chunk_index") or 0)
                    DocumentChunk.objects.update_or_create(
                        document=document,
                        chunk_index=chunk_index,
                        defaults={
                            "section": f"Source chunk {chunk_index}",
                            "page": chunk.get("page"),
                            "text": source_content(chunk, registry.get(source_id)),
                            "token_count": len(str(chunk.get("text", "")).split()),
                            "metadata": {"dataset": DATASET_VERSION, "source_id": source_id},
                        },
                    )
                    documents_seen += 1
                    chunks_created += 1

            run.status = "complete"
            run.documents_seen = documents_seen
            run.chunks_created = chunks_created
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "documents_seen", "chunks_created", "finished_at"])
        except Exception as exc:
            run.status = "failed"
            run.failed_records = [{"error": str(exc)}]
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "failed_records", "finished_at"])
            raise

        self.stdout.write(self.style.SUCCESS(
            f"Ingested {documents_seen} dataset documents / {chunks_created} chunks"
        ))

    @staticmethod
    def read_jsonl(archive, name):
        with archive.open(name) as handle:
            return [json.loads(line) for line in handle.read().decode("utf-8").splitlines() if line.strip()]

    @staticmethod
    def upsert_standard(record, document, title, standard):
        if not standard:
            return
        metadata = record.get("live_bis_standard_metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        StandardRecord.objects.update_or_create(
            number=str(standard)[:120],
            defaults={
                "title": str(metadata.get("title") or title)[:500],
                "aspect": "Dataset regulatory record",
                "language": "en",
                "department": str(record.get("sector") or "Dataset")[:200],
                "scope": str(record.get("product_title_canonical") or title),
                "is_demo": True,
                "source_document": document,
            },
        )