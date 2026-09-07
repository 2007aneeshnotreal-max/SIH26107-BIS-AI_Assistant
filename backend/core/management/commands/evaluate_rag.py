import json
from pathlib import Path
from django.core.management.base import BaseCommand
from core.models import EvaluationResult
from core.services.gemini import MockGeminiProvider
from core.services.rag import RagAnswerService

class Command(BaseCommand):
    def add_arguments(self, parser): parser.add_argument("--dataset", required=True)
    def handle(self, *args, **options):
        rows=[json.loads(x) for x in Path(options["dataset"]).read_text().splitlines() if x.strip()]
        service=RagAnswerService(provider=MockGeminiProvider()); totals={"hit":0,"valid":0,"abstain_correct":0}
        for row in rows:
            result=service.answer(row["question"], row.get("language","en")); ids=result.trace["retrieved_source_ids"]
            hit=any(row.get("expected_standard","") in x.chunk.document.standard_number for x in result.citations) if row.get("expected_standard") else result.abstained
            totals["hit"]+=int(hit); totals["valid"]+=int(bool(result.citations) or result.abstained); totals["abstain_correct"]+=int(result.abstained==row.get("should_abstain",False))
            EvaluationResult.objects.create(run_label="mock", question=row["question"], expected_source=row.get("expected_standard",""), metrics={"hit":hit,"citation_valid":bool(result.citations) or result.abstained,"abstained":result.abstained,"retrieved":ids})
        count=max(len(rows),1); report="# ManakSetu RAG evaluation\n\n"+"\n".join([f"- {key}: {value/count:.1%}" for key,value in totals.items()])
        Path("evaluation-report.md").write_text(report+"\n")
        self.stdout.write(report)

