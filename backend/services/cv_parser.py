# services/cv_parser.py
# Extracts text from PDF/DOCX files and uses LLM to parse
# structured candidate data from the raw text.
#
# Flow:
#   1. Read file bytes → extract raw text
#   2. Send raw text to LLM → get structured JSON
#   3. Return parsed candidate profile

import json
from io import BytesIO
from PyPDF2 import PdfReader
from docx import Document
from langchain_openai import ChatOpenAI
from backend.config import OPENAI_API_KEY

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    temperature=0
)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text from a PDF file.
    
    BytesIO wraps raw bytes so PdfReader can read it like a file.
    We loop through every page and concatenate the text.
    """
    reader = PdfReader(BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extract text from a DOCX file.
    
    python-docx reads the file and gives us paragraphs.
    Each paragraph is a block of text in the document.
    """
    doc = Document(BytesIO(file_bytes))
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Route to the correct extractor based on file extension.
    """
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {filename}. Use PDF or DOCX.")


def parse_cv_with_llm(raw_text: str) -> dict:
    """
    Send raw CV text to LLM and get structured candidate data.
    
    The LLM is instructed to return ONLY JSON — no markdown,
    no explanation, just the JSON object.
    
    Returns dict with: name, email, phone, skills, experience,
    education, projects
    """
    prompt = f"""Parse the following CV/resume text and extract structured information.
Return ONLY a valid JSON object with these fields:
{{
    "name": "candidate full name",
    "email": "email address or null",
    "phone": "phone number or null",
    "skills": ["skill1", "skill2", ...],
    "experience": [
        {{
            "role": "job title",
            "company": "company name",
            "dates": "start - end",
            "description": "brief description"
        }}
    ],
    "education": [
        {{
            "degree": "degree name",
            "institution": "school name",
            "dates": "start - end"
        }}
    ],
    "projects": [
        {{
            "name": "project name",
            "description": "brief description"
        }}
    ]
}}

Return ONLY the JSON. No markdown backticks, no explanation.

CV Text:
{raw_text}"""

    response = llm.invoke(prompt)
    response_text = response.content.strip()

    # Clean up LLM response — sometimes it wraps in ```json ... ```
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1]  # remove first line
        response_text = response_text.rsplit("```", 1)[0]  # remove last ```

    try:
        parsed = json.loads(response_text)
        return parsed
    except json.JSONDecodeError:
        # If LLM returns invalid JSON, return raw text as fallback
        return {
            "name": "Parse Error",
            "email": None,
            "phone": None,
            "skills": [],
            "experience": [],
            "education": [],
            "projects": [],
            "raw_text": raw_text[:1000]
        }


async def parse_cv(file_bytes: bytes, filename: str) -> dict:
    """
    Main function — called by the upload endpoint.
    
    1. Extract raw text from file
    2. Parse with LLM
    3. Return structured data + raw text
    """
    raw_text = extract_text(file_bytes, filename)

    if not raw_text.strip():
        raise ValueError("Could not extract any text from the file.")

    parsed_data = parse_cv_with_llm(raw_text)
    parsed_data["raw_text"] = raw_text  # keep original for reference

    return parsed_data