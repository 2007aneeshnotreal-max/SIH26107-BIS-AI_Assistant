import uuid
from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SourceDocument(TimestampedModel):
    class SourceType(models.TextChoices):
        DEMO = "demo", "Demo fixture"
        OFFICIAL = "official", "Official public source"
        USER = "user", "User supplied"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    document_id = models.CharField(max_length=120)
    version = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=500)
    standard_number = models.CharField(max_length=120, blank=True, db_index=True)
    source_type = models.CharField(max_length=20, choices=SourceType.choices, default=SourceType.DEMO, db_index=True)
    source_url = models.URLField(blank=True)
    language = models.CharField(max_length=12, default="en", db_index=True)
    category = models.CharField(max_length=100, blank=True, db_index=True)
    publication_date = models.DateField(null=True, blank=True)
    content = models.TextField()
    checksum = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["document_id", "version"], name="unique_document_version")]
        indexes = [models.Index(fields=["category", "language"])]

    def __str__(self):
        return f"{self.document_id} v{self.version}"


class DocumentChunk(models.Model):
    document = models.ForeignKey(SourceDocument, related_name="chunks", on_delete=models.PROTECT)
    chunk_index = models.PositiveIntegerField()
    section = models.CharField(max_length=300, blank=True)
    page = models.PositiveIntegerField(null=True, blank=True)
    text = models.TextField()
    token_count = models.PositiveIntegerField(default=0)
    vector_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["document", "chunk_index"], name="unique_document_chunk")]


class IngestionRun(TimestampedModel):
    status = models.CharField(max_length=20, default="pending", db_index=True)
    source_path = models.CharField(max_length=500)
    documents_seen = models.PositiveIntegerField(default=0)
    chunks_created = models.PositiveIntegerField(default=0)
    failed_records = models.JSONField(default=list, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)


class StandardRecord(TimestampedModel):
    number = models.CharField(max_length=120, unique=True)
    title = models.CharField(max_length=500)
    equivalent_standard = models.CharField(max_length=120, blank=True)
    supersedes = models.CharField(max_length=120, blank=True)
    equivalence = models.CharField(max_length=100, blank=True)
    revision_count = models.PositiveIntegerField(default=0)
    amendment_count = models.PositiveIntegerField(default=0)
    aspect = models.CharField(max_length=100, db_index=True)
    language = models.CharField(max_length=12, default="en", db_index=True)
    department = models.CharField(max_length=200, db_index=True)
    committee = models.CharField(max_length=300, blank=True)
    member_secretary = models.CharField(max_length=200, blank=True)
    scope = models.TextField()
    is_demo = models.BooleanField(default=True)
    source_document = models.ForeignKey(SourceDocument, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.number} — {self.title}"


class ChatSession(TimestampedModel):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=200, default="New standards conversation")
    audience = models.CharField(max_length=20, default="industry")
    language = models.CharField(max_length=12, default="en")
    is_pinned = models.BooleanField(default=False, db_index=True)


class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, related_name="messages", on_delete=models.CASCADE)
    role = models.CharField(max_length=20)
    content = models.TextField()
    intent = models.CharField(max_length=60, blank=True, db_index=True)
    confidence = models.FloatField(null=True, blank=True)
    abstained = models.BooleanField(default=False)
    trace = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Citation(models.Model):
    message = models.ForeignKey(ChatMessage, related_name="citations", on_delete=models.CASCADE)
    chunk = models.ForeignKey(DocumentChunk, on_delete=models.PROTECT)
    label = models.CharField(max_length=300)
    ordinal = models.PositiveIntegerField()

    class Meta:
        ordering = ["ordinal"]


class CertificationRecord(TimestampedModel):
    identifier = models.CharField(max_length=100, unique=True)
    identifier_type = models.CharField(max_length=30, default="licence")
    status = models.CharField(max_length=30, db_index=True)
    organization = models.CharField(max_length=300)
    product_scope = models.CharField(max_length=500)
    standard_number = models.CharField(max_length=120, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_demo = models.BooleanField(default=True)


class ApplicationGuide(TimestampedModel):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=300)
    summary = models.TextField()
    scheme = models.CharField(max_length=120, db_index=True)
    language = models.CharField(max_length=12, default="en")
    is_demo = models.BooleanField(default=True)


class ApplicationStep(models.Model):
    guide = models.ForeignKey(ApplicationGuide, related_name="steps", on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    title = models.CharField(max_length=300)
    description = models.TextField()
    checklist = models.JSONField(default=list)
    links = models.JSONField(default=list)
    estimated_next_step = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["order"]
        constraints = [models.UniqueConstraint(fields=["guide", "order"], name="unique_guide_step")]


class Feedback(models.Model):
    message = models.ForeignKey(ChatMessage, null=True, blank=True, on_delete=models.SET_NULL)
    rating = models.SmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SafetyAlert(TimestampedModel):
    title = models.CharField(max_length=300)
    summary = models.TextField()
    severity = models.CharField(max_length=20, default="info")
    source_url = models.URLField(blank=True)
    is_demo = models.BooleanField(default=True)
    active = models.BooleanField(default=True)


class EvaluationResult(models.Model):
    run_label = models.CharField(max_length=100)
    question = models.TextField()
    expected_source = models.CharField(max_length=120, blank=True)
    metrics = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
