"""Normalize the supplied BIS prototype/reference schema for retrieval."""
import json
import re


def flatten(value, prefix=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from flatten(item, f"{prefix}.{key}" if prefix else key)
    elif isinstance(value, list):
        for index, item in enumerate(value, 1):
            yield from flatten(item, f"{prefix}[{index}]")
    else:
        yield f"{prefix}: {json.dumps(value, ensure_ascii=False)}"


def normalize_record(record):
    if record.get("record_type") not in {"standard_with_certification", "reference_standard"}:
        return record
    if not isinstance(record.get("is_synthetic"), bool):
        raise ValueError("BIS records must specify is_synthetic as a boolean")
    synthetic = record["is_synthetic"]
    view, download = record["view"], record["download"]
    number = view["IS Number"]
    label = ("SYNTHETIC DEMO: fictional record; no official BIS approval or legal validity."
             if synthetic else "USER-SUPPLIED REFERENCE: earlier compilation; not newly revalidated; not a certificate or licence.")
    header = f"{label}\nProduct: {record['product_name']}\nStandard: {number}\nRecord: {record['record_id']}"
    metadata = {key: record.get(key) for key in (
        "record_id", "is_synthetic", "source_type", "legal_validity", "as_of_date", "provenance", "pdf_location")}
    sections = []
    for key in ("view", "download", "standards_catalogue", "product_certification", "consumer_information", "provenance"):
        if record.get(key) is None:
            continue
        # Bound each passage, repeating provenance so it survives retrieval alone.
        words = "\n".join(flatten(record[key], key)).split()
        for start in range(0, len(words), 180):
            sections.append({"section": f"{key} {start // 180 + 1}",
                             "text": header + "\n" + " ".join(words[start:start + 180]),
                             "metadata": metadata})
    return {
        "document_id": record["record_id"], "version": int(record.get("version", 1)),
        "title": f"{record['product_name']} — {view['IS Title']}",
        "standard_number": number, "source_type": "demo" if synthetic else "user",
        "source_url": "" if synthetic else (download.get("URL") or ""),
        "category": record["category"], "language": "en",
        "content": json.dumps(record, ensure_ascii=False, sort_keys=True),
        "chunks": sections,
    }


def dataset_answer(evidence, question):
    """Readable extractive fallback when the generation provider is unavailable."""
    top = evidence[0]
    question_words = set(re.findall(r"[a-z]+", question.lower()))
    fields = top["fields"]
    section = top["section"].split()[0]
    selected = {}
    if section == "product_certification":
        if question_words & {"licence", "license", "holder"}:
            selected = {key: value for key, value in fields.get("licence", {}).items()
                        if key in {"licence_id", "status", "holder", "product_scope", "valid_from", "valid_to", "legal_validity"}}
        elif question_words & {"certificate", "cert"}:
            selected = {key: value for key, value in fields.get("certificate", {}).items()
                        if key in {"certificate_id", "status", "issuer", "scope", "issue_date", "expiry_date", "legal_validity"}}
        elif question_words & {"apply", "application", "fee", "fees", "documents"}:
            selected = fields.get("application", {})
        else:
            selected = {key: fields[key] for key in ("scheme_name", "product_specific_requirements", "grant_of_licence") if key in fields}
    elif section == "consumer_information":
        if question_words & {"complaint", "complain", "complaints"}:
            selected = {key: fields[key] for key in ("BIS_complaint_process", "complaint_id", "complaint_status", "complaint_topic", "how_to_lodge_complaints") if key in fields}
        elif question_words & {"contact", "email", "phone", "office"}:
            selected = fields.get("BIS_contact_information", {})
        elif question_words & {"hallmark", "huid"}:
            selected = {"Hallmark verification": fields.get("Hallmark_verification")}
        else:
            selected = {"Product authenticity": fields.get("product_authenticity"), "Standard mark": fields.get("Standard_Mark")}
    elif section == "download":
        selected = {key: fields[key] for key in ("scope", "section", "scope_is_paraphrased", "full_standard_downloaded") if key in fields}
    elif section == "view":
        selected = {key: value for key, value in fields.items() if key not in {"IS Number", "IS Title"}}
    else:
        selected = fields

    lines = []
    for key, value in selected.items():
        if value is None:
            continue
        if top.get("is_synthetic") and (key.endswith("_id") or key in {"document_name", "document_type", "scheme_name"}):
            continue
        label = key.replace("_", " ").removeprefix("BIS ").capitalize()
        if isinstance(value, list):
            value = "; ".join(str(item) for item in value)
        elif isinstance(value, bool):
            value = "Yes" if value else "No"
        lines.append(f"- {label}: {value}")
    provenance = top.get("provenance", {})
    if not top.get("is_synthetic"):
        for key in ("source_note", "access_limitation", "verification_level"):
            if provenance.get(key):
                lines.append(f"- {key.replace('_', ' ').capitalize()}: {provenance[key]}")
    heading = top.get('product_name', top['title'])
    if not top.get("is_synthetic"):
        heading = f"{top['standard_number']} — {heading}"
    return heading + "\n\n" + "\n".join(lines)
