# ev_adaptor.py
import os, sys, json
from io import BytesIO
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient

# ---------------- Env & client ----------------
load_dotenv()

AZURE_DI_ENDPOINT = os.getenv("AZURE_DI_ENDPOINT")
AZURE_DI_KEY = os.getenv("AZURE_DI_KEY")
EV_MODEL_ID = os.getenv("EV_MODEL_ID", "EmploymentVerificationExtractor4")

if not AZURE_DI_ENDPOINT or not AZURE_DI_KEY:
    print("❌ Missing AZURE_DI_ENDPOINT or AZURE_DI_KEY in environment.")
    sys.exit(1)

di_client = DocumentIntelligenceClient(
    endpoint=AZURE_DI_ENDPOINT,
    credential=AzureKeyCredential(AZURE_DI_KEY),
)

def _begin_analyze(model_id: str, file_bytes: bytes, **kwargs):
    """Wrapper for body/document arg differences"""
    try:
        return di_client.begin_analyze_document(
            model_id=model_id,
            document=BytesIO(file_bytes),
            **kwargs,
        )
    except TypeError:
        return di_client.begin_analyze_document(
            model_id=model_id,
            body=BytesIO(file_bytes),
            **kwargs,
        )

def extract_ev_structured(file_bytes: bytes) -> dict:
    """
    Just extract fields from EV custom model.
    Returns JSON like paystub_adaptor: 
    { field: {"value": ..., "confidence": ...}, ... }
    """
    poller = _begin_analyze(
        model_id=EV_MODEL_ID,
        file_bytes=file_bytes,
        content_type="application/octet-stream",
        polling=True,
    )
    result = poller.result()

    doc = result.documents[0] if getattr(result, "documents", []) else None
    out = {}

    if doc and getattr(doc, "fields", None):
        for key, field in doc.fields.items():
            out[str(key)] = {
                "value": getattr(field, "content", None),
                "confidence": round(getattr(field, "confidence", 0) * 100, 2)
                              if getattr(field, "confidence", None) else None
            }

    return out

# ---------------- CLI ----------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ev_adaptor.py <path_to_ev_document>")
        sys.exit(1)

    file_path = sys.argv[1]
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    fields = extract_ev_structured(file_bytes)
    print(json.dumps(fields, indent=2))
