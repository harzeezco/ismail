import json
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
from groq import Groq
from dotenv import load_dotenv
import ollama

# --- 1. Define Split Schemas ---

class Contact(BaseModel):
    email: Optional[str] = None
    linkedin: Optional[str] = None
    portfolio: Optional[str] = None


class PersonalInfo(BaseModel):
    name: str
    headline: str
    location: str
    contact: Contact

# Schema for Pass 1


class ProfileOverview(BaseModel):
    personal_info: PersonalInfo
    summary: str
    skills_and_tools: List[str]
    languages: List[str]
    certifications: List[str]


class Experience(BaseModel):
    company: str
    role: str
    duration: str
    location: Optional[str] = None
    description: Optional[str] = None
    highlights: List[str]


class Education(BaseModel):
    institution: str
    degree: str
    duration: Optional[str] = None

# Schema for Pass 2


class ProfileHistory(BaseModel):
    experience: List[Experience]
    education: List[Education]

# Final Merged Schema


class PortfolioSchema(BaseModel):
    personal_info: PersonalInfo
    summary: str
    skills_and_tools: List[str]
    languages: List[str]
    certifications: List[str]
    experience: List[Experience]
    education: List[Education]


MINIFIED_SCHEMA_PROMPT = """
{
  "personal_info": {
    "name": "str", "headline": "str", "location": "str",
    "contact": {"email": "str|null", "linkedin": "str|null", "portfolio": "str|null"}
  },
  "summary": "str",
  "skills_and_tools": ["str"],
  "languages": ["str"],
  "certifications": ["str"],
  "experience": [{
    "company": "str", "role": "str", "duration": "str", "location": "str|null",
    "description": "str|null", "highlights": ["str"]
  }],
  "education": [{
    "institution": "str", "degree": "str", "duration": "str|null"
  }]
}
"""

def clean_json_output(raw_text):
    """Strips Markdown backticks and trailing artifacts."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

def parse_md_with_ollama(md_file_path, json_file_path):
    print(f"[*] Reading Markdown from '{md_file_path}'...")

    raw_md = Path(md_file_path).read_text(encoding="utf-8")
    compressed_md = "\n".join(
        [line for line in raw_md.split("\n") if line.strip()])

    print("[*] Sending payload to Local Ollama model. This may take a moment depending on your hardware...")

    # 3. Call the local Ollama instance
    response = ollama.chat(
        model='gpt-oss:20b-cloud',
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict JSON extraction engine. Extract the resume text into JSON matching the exact keys below. "
                    "Output ONLY valid JSON.\n\n"
                    f"SCHEMA PROTOTYPE:\n{MINIFIED_SCHEMA_PROMPT}"
                )
            },
            {"role": "user", "content": compressed_md}
        ],
        # Force Ollama to only output valid JSON
        format='json',
        options={
            "temperature": 0.0  # Deterministic output
        }
    )

    raw_text = response['message']['content']

    try:
        # 4. Validate the response against our strict Pydantic rules
        extracted_data = PortfolioSchema.model_validate_json(raw_text)

        with open(json_file_path, "w", encoding="utf-8") as f:
            f.write(extracted_data.model_dump_json(indent=4))
        print(
            f"[+] SUCCESS: Local Ollama extraction saved to '{json_file_path}'")

    except Exception as e:
        print("[-] Validation Failed.")
        with open("debug_raw_output.txt", "w", encoding="utf-8") as f:
            f.write(raw_text)
        print(f"Error: {e}\nRaw output saved for inspection.")
