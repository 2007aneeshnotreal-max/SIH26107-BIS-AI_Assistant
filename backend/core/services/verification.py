from core.models import CertificationRecord

class VerificationService:
    def check(self, identifier: str):
        try:
            record = CertificationRecord.objects.get(identifier__iexact=identifier.strip())
        except CertificationRecord.DoesNotExist:
            return {"found": False, "mode": "mock", "official": False, "message": "No matching record exists in the seeded demo dataset. This is not an official BIS result."}
        return {"found": True, "mode": "mock" if record.is_demo else "provider", "official": not record.is_demo,
                "identifier": record.identifier, "identifier_type": record.identifier_type, "status": record.status,
                "organization": record.organization, "product_scope": record.product_scope,
                "standard_number": record.standard_number, "issue_date": record.issue_date, "expiry_date": record.expiry_date,
                "message": "Demo fixture only. Confirm through an official BIS channel." if record.is_demo else "Provider-backed result."}

