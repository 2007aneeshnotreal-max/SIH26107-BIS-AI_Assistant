from django.contrib import admin
from .models import (ApplicationGuide, ApplicationStep, CertificationRecord, ChatMessage,
                     ChatSession, Citation, DocumentChunk, Feedback, IngestionRun,
                     SafetyAlert, SourceDocument, StandardRecord)

class ChunkInline(admin.TabularInline):
    model = DocumentChunk
    extra = 0
    readonly_fields = ("chunk_index", "section", "page", "token_count", "vector_id")

@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
    list_display = ("document_id", "version", "title", "source_type", "language", "is_active")
    list_filter = ("source_type", "language", "category", "is_active")
    search_fields = ("document_id", "standard_number", "title")
    inlines = [ChunkInline]

admin.site.register([StandardRecord, CertificationRecord, ApplicationGuide, ApplicationStep,
                     ChatSession, ChatMessage, Citation, Feedback, IngestionRun, SafetyAlert])

