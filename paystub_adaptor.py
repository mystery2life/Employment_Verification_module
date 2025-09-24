import os, json, sys
from io import BytesIO
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentAnalysisFeature
from openai import AzureOpenAI

# ---------------- Config ----------------
load_dotenv()

AZURE_DI_ENDPOINT = os.getenv("AZURE_DI_ENDPOINT")
AZURE_DI_KEY = os.getenv("AZURE_DI_KEY")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# ---------------- Clients ----------------
di_client = DocumentIntelligenceClient(
    endpoint=AZURE_DI_ENDPOINT,
    credential=AzureKeyCredential(AZURE_DI_KEY)
)

aoai_client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# ---------------- Helpers ----------------
def begin_analyze(model_id: str, file_bytes: bytes, **kwargs):
    """DI client wrapper to work with body/document arg differences"""
    try:
        return di_client.begin_analyze_document(
            model_id=model_id,
            document=BytesIO(file_bytes),
            **kwargs
        )
    except TypeError:
        return di_client.begin_analyze_document(
            model_id=model_id,
            body=BytesIO(file_bytes),
            **kwargs
        )

def extract_paystub_structured(file_bytes: bytes):
    poller = begin_analyze(
        "prebuilt-payStub.us",
        file_bytes,
        content_type="application/octet-stream",
        features=[DocumentAnalysisFeature.QUERY_FIELDS],
        polling=True,
    )
    result = poller.result()
    doc = result.documents[0] if getattr(result, "documents", []) else None
    out = {}
    if doc:
        for key, field in doc.fields.items():
            out[key] = {
                "value": getattr(field, "content", None),
                "confidence": round(getattr(field, "confidence", 0) * 100, 2)
            }
    return out

def extract_read_text(file_bytes: bytes) -> str:
    poller = begin_analyze("prebuilt-read", file_bytes, polling=True)
    result = poller.result()
    return "\n".join([ln.content for pg in result.pages for ln in pg.lines])

# --- LLM Prompt ---
EXTRACTION_PROMPT = """
You are a payroll document expert. From the following pay stub text, extract these fields:

1. TotalHoursWorked — the total of all hours worked across categories like Regular, Overtime, Holiday, Sick, etc. Give only float value. If not listed, return null.
2. AveragePayRate — Use all available hour-rate pairs and compute weighted average as (rate × hours) summed and divided by total hours. Return float values rounded to 2 decimal places. If only one rate exists, just return it. ONLY extract the hourly pay rate. Ignore if it is monthly or daily pay rate. Give only float value. If not listed, return null.
3. JobTitle — the job title of the employee (like "Maintenance", "Driver"). If not listed, return null.

For each field, also return a confidence score (0–100). Confidence represents how certain you are that the extracted value is correct, where:
- 100 = absolutely certain
- 80+ = strong match
- 50–79 = moderate guess
- below 50 = very uncertain

⚠️ OUTPUT RULES ⚠️
- Respond with one JSON object ONLY.
- Do NOT include markdown, code fences, explanations, or extra text.
- The JSON MUST be in this exact shape:

Return only **pure JSON** in this exact format:
{{
  "TotalHoursWorked": {{"value": float|null, "confidence": int}},
  "AveragePayRate": {{"value": float|null, "confidence": int}},
  "JobTitle": {{"value": string|null, "confidence": int}}
}}

Here is the pay stub text:
\"\"\"{text}\"\"\"

JSON:
"""


def extract_llm_fields(text: str):
    prompt = EXTRACTION_PROMPT.format(text=text[:2000])
    resp = aoai_client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": "Extract fields in JSON only"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
    )
    raw = resp.choices[0].message.content.strip()
            # 👇 Debug: print the entire raw response from LLM
    #print("========== RAW LLM RESPONSE ==========")
    #print(raw)
    #print("=====================================")
        # --- Strip Markdown fences if present ---
    if raw.startswith("```"):
        raw = raw.strip("`")          # remove all backticks
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()     # drop "json" label

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("⚠️ Could not parse LLM JSON, returning raw text instead")
        return {"raw_response": raw}

# ---------------- Main ----------------
def process_paystub(file_bytes: bytes, filename: str):
    print(f"[paystub] Processing {filename}")

    structured = extract_paystub_structured(file_bytes)
    print("Structured fields:", structured.keys())

    text = extract_read_text(file_bytes)
    llm_fields = extract_llm_fields(text)
    print("LLM fields:", llm_fields)

    # Merge: structured first, fill gaps with LLM
    for k_map in [("TotalHours", "TotalHoursWorked"),
                  ("AveragePayRate", "AveragePayRate"),
                  ("JobTitle", "JobTitle")]:
        out_key, llm_key = k_map
        if out_key not in structured or not structured[out_key].get("value"):
            structured[out_key] = {
                "value": llm_fields.get(llm_key),
                "confidence": 80.0
            }

    return {
        "status": "success",
        "filename": filename,
        "extracted_fields": structured
    }

# ---------------- CLI ----------------
import sys
import json

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python paystub_adaptor.py <path_to_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # Run both structured + read + LLM steps
    structured = extract_paystub_structured(file_bytes)
    raw_text = extract_read_text(file_bytes)
    llm_fields = extract_llm_fields(raw_text)  # make sure you have this function

    combined = {**structured, **llm_fields}
    print(json.dumps(combined, indent=2))
