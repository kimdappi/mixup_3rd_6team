from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedDocument:
    document_type: str
    text: str


def extract_text_from_upload(filename: str, content: bytes) -> ExtractedDocument:
    text = content.decode("utf-8", errors="ignore")
    lowered = filename.lower()
    if "registry" in lowered or "등기" in filename:
        document_type = "registry"
    elif "ledger" in lowered or "건축물" in filename:
        document_type = "building_ledger"
    elif "contract" in lowered or "계약" in filename:
        document_type = "contract"
    else:
        document_type = "unknown"
    return ExtractedDocument(document_type=document_type, text=text)
