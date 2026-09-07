class CitationService:
    """Ensures a model can cite only chunks present in its retrieval envelope."""
    def validate(self, requested_ids: list[str], retrieved_ids: list[str]) -> tuple[list[str], bool]:
        allowed = set(retrieved_ids)
        valid = [source_id for source_id in requested_ids if source_id in allowed]
        return valid, len(valid) == len(requested_ids)

