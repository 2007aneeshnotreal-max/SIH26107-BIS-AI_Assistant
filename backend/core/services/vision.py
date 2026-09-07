import json
import os
from dataclasses import dataclass

from .gemini import AIProviderError


@dataclass
class ProductDetection:
    product: str
    brand: str
    confidence: float
    visible_details: list[str]


class VisionService:
    def analyze(self, data: bytes, mime_type: str, filename: str) -> ProductDetection:
        if os.getenv("AI_PROVIDER", "mock") != "gemini" or not os.getenv("GEMINI_API_KEY"):
            name = filename.lower()
            product = "electric kettle" if "kettle" in name else ""
            return ProductDetection(product, "", .65 if product else 0, [])
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            schema = {"type":"object","properties":{"product":{"type":"string"},"brand":{"type":"string"},"confidence":{"type":"number"},"visible_details":{"type":"array","items":{"type":"string"}}},"required":["product","brand","confidence","visible_details"]}
            prompt = "Identify the main consumer or industrial product in this image. Read the brand/manufacturer only when visibly supported; otherwise return an empty brand. Do not guess. Record useful visible ratings, labels, marks, capacity, model, and materials. Return JSON."
            response = client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), contents=[prompt, types.Part.from_bytes(data=data, mime_type=mime_type)], config={"response_mime_type":"application/json","response_json_schema":schema})
            parsed=json.loads(response.text)
            return ProductDetection(str(parsed.get("product","")).strip(),str(parsed.get("brand","")).strip(),float(parsed.get("confidence",0)),[str(x) for x in parsed.get("visible_details",[])][:8])
        except Exception as exc:
            raise AIProviderError(f"Image analysis failed: {exc}") from exc
