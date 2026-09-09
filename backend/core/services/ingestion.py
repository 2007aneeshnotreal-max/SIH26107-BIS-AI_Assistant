import os
from pathlib import Path
from bs4 import BeautifulSoup
from pypdf import PdfReader

ALLOWED_SUFFIXES={".pdf",".html",".htm",".md",".txt",".csv",".json",".jsonl"}
MAX_BYTES=int(os.getenv("INGESTION_MAX_BYTES",str(10*1024*1024)))

class IngestionService:
    def validate(self,path:Path):
        if path.suffix.lower() not in ALLOWED_SUFFIXES: raise ValueError(f"Unsupported source type: {path.suffix}")
        if path.stat().st_size>MAX_BYTES: raise ValueError(f"File exceeds {MAX_BYTES} bytes")
    def extract(self,path:Path):
        self.validate(path); suffix=path.suffix.lower()
        if suffix==".pdf":
            reader=PdfReader(str(path)); return [{"content":page.extract_text() or "","page":index+1,"title":path.stem} for index,page in enumerate(reader.pages)]
        if suffix in {".html",".htm"}:
            soup=BeautifulSoup(path.read_text(encoding="utf-8"),"html.parser")
            for node in soup(["script","style","nav"]): node.decompose()
            return [{"content":soup.get_text("\n"),"title":soup.title.string if soup.title and soup.title.string else path.stem}]
        return [{"content":path.read_text(encoding="utf-8"),"title":path.stem}]

