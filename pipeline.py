import os
import requests
import firebase_admin
from firebase_admin import credentials, firestore

# ---- PATHS ----
DEFAULT_SERVICE_KEY_PATH = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
SERVICE_KEY_PATH = os.getenv("SERVICE_ACCOUNT_KEY_PATH", DEFAULT_SERVICE_KEY_PATH)

# ---- OLLAMA ----
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

# ---- KEYWORD MAP ----
# Maps user query words → Firestore document IDs
# (Matches the same logic the voice pipeline uses)
KEYWORD_MAP = {
    "disability": "disability_rights",
    "rights": "disability_rights",
    "right": "disability_rights",
    "access": "accessibility_laws",
    "wheelchair": "accessibility_laws",
    "education": "education_for_pwd",
    "school": "education_for_pwd",
    "health": "health_services_pwd",
    "hospital": "health_services_pwd",
    "job": "employment_pwd",
    "work": "employment_pwd",
    "employment": "employment_pwd",
}

_db = None

def _get_db():
    """Connect to Firestore once and reuse the connection."""
    global _db
    if _db is None:
        if not os.path.exists(SERVICE_KEY_PATH):
            raise FileNotFoundError(
                f"Service account key not found at '{SERVICE_KEY_PATH}'. "
                "Set SERVICE_ACCOUNT_KEY_PATH to your local key file path."
            )
        cred = credentials.Certificate(SERVICE_KEY_PATH)
        try:
            firebase_admin.initialize_app(cred)
        except ValueError:
            pass  # already initialized from a previous request
        _db = firestore.client()
        print("✅ Firestore connected")
    return _db

def match_topic(user_text: str) -> str | None:
    """Match user text to a Firestore document ID using keywords."""
    text_lower = user_text.lower()

    for keyword, topic_id in KEYWORD_MAP.items():
        if keyword in text_lower:
            print(f"🔍 Matched keyword '{keyword}' → topic '{topic_id}'")
            return topic_id

    print(f"⚠️ No keyword match for: '{user_text}'")
    return None

def fetch_content(topic_id: str, language: str = "en") -> str | None:
    """Fetch pre-approved civic content from Firestore.

    Args:
        topic_id: Firestore document ID (e.g., 'disability_rights')
        language: 'en' for English, 'sw' for Kiswahili
    """
    db = _get_db()
    doc = db.collection("civic_content").document(topic_id).get()

    if not doc.exists:
        print(f"⚠️ Document '{topic_id}' not found")
        return None

    field = f"body_{language}"
    content = doc.to_dict().get(field)

    if not content:
        print(f"⚠️ Field '{field}' missing in document '{topic_id}'")
        return None

    print(f"📄 Fetched content for '{topic_id}' ({len(content)} chars)")
    return content

def simplify_text(raw_text: str) -> str:
    """Use Ollama to simplify civic content into plain language."""

    prompt = f"""You are a plain-language civic assistant called Fahamika.
Rewrite the following civic information into clear, simple language.
Use short sentences. Do NOT add any new facts — only rewrite what is given.

Original text:
{raw_text}

Simplified version:"""

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()["response"].strip()
        print(f"🤖 AI simplified ({len(raw_text)} → {len(result)} chars)")
        return result
    except requests.exceptions.RequestException as e:
        print(f"❌ Ollama error: {e}")
        return raw_text  # fallback: return unsimplified text
    
def process_message(user_text: str, language: str = "en") -> str:
    """Run the full pipeline: match → fetch → simplify → reply.

    Args:
        user_text: The SMS text from the user
        language: 'en' or 'sw'

    Returns:
        The simplified civic content, or a fallback message
    """
    # Step 1: Match topic
    topic_id = match_topic(user_text)
    if topic_id is None:
        return ("Sorry, I couldn't understand your question. "
                "Try asking about: disability rights, education, "
                "health services, employment, or accessibility laws.")

    # Step 2: Fetch from Firestore
    content = fetch_content(topic_id, language)
    if content is None:
        return (f"Sorry, information about '{topic_id}' is not yet "
                "available. We are adding new topics regularly.")

    # Step 3: Simplify with AI
    simplified = simplify_text(content)

    return simplified