import hashlib
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from pypdf import PdfReader

from core.models import DocumentChunk, IngestionRun, SourceDocument
from core.services.chunking import chunk_text


SUPPORTED_SUFFIXES = {".pdf", ".docx"}
DATASET_LABEL = "User-provided BIS citation dataset"


def extract_docx(data):
    with zipfile.ZipFile(data) as document:
        xml = document.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs = []
    for paragraph in root.iter(f"{namespace}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t"))
        if text.strip():
            paragraphs.append(text.strip())
    return "\n".join(paragraphs)


def document_id(relative_name):
    digest = hashlib.sha256(relative_name.encode("utf-8")).hexdigest()[:16]
    return f"CITATION-{digest}"


class Command(BaseCommand):
    help = "Import PDF and DOCX files from a citation dataset ZIP as page-aware evidence."

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True, help="Path to citation data ZIP")

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
                files = [
                    name for name in archive.namelist()
                    if not name.endswith("/")
                    and not Path(name).name.startswith("~$")
                    and Path(name).suffix.lower() in SUPPORTED_SUFFIXES
                ]
                if not files:
                    raise CommandError("The archive contains no PDF or DOCX files")

                for name in files:
                    suffix = Path(name).suffix.lower()
                    if suffix == ".pdf":
                        pages = self.extract_pdf(archive, name)
                    else:
                        pages = [{"page": None, "text": extract_docx(archive.open(name))}]
                    content = "\n\n".join(page["text"] for page in pages if page["text"].strip())
                    if not content.strip():
                        continue

                    relative_name = name.replace("\\", "/")
                    document, _ = SourceDocument.objects.update_or_create(
                        document_id=document_id(relative_name),
                        version=1,
                        defaults={
                            "title": relative_name[:500],
                            "source_type": SourceDocument.SourceType.USER,
                            "language": "en",
                            "category": "citation_dataset",
                            "content": f"Dataset: {DATASET_LABEL}\nFile: {relative_name}\n{content}",
                            "checksum": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        },
                    )
                    document.chunks.all().delete()
                    document_chunk_index = 0
                    for page in pages:
                        for item in chunk_text(page["text"]):
                            DocumentChunk.objects.create(
                                document=document,
                                chunk_index=document_chunk_index,
                                section=item.section or "Document text",
                                page=page["page"],
                                text=f"Dataset: {DATASET_LABEL}\nFile: {relative_name}\n{item.text}",
                                token_count=len(item.text.split()),
                                metadata={
                                    "dataset": DATASET_LABEL,
                                    "archive_path": relative_name,
                                    "page": page["page"],
                                },
                            )
                            document_chunk_index += 1
                            chunks_created += 1
                    documents_seen += 1

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
            f"Imported {documents_seen} citation documents / {chunks_created} chunks"
        ))

    @staticmethod
    def extract_pdf(archive, name):
        with archive.open(name) as handle:
            reader = PdfReader(handle)
            return [{"page": index + 1, "text": page.extract_text() or ""} for index, page in enumerate(reader.pages)]