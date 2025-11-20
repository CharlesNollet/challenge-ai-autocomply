"""API client for vision and text endpoints"""
import time
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class APIClient:
    """Client for making API calls to vision and text endpoints."""
    
    def __init__(self, api_url: str, api_key: str, max_retries: int = 3):
        """Initialize API client.
        
        Args:
            api_url: Base URL for API
            api_key: API authentication key
            max_retries: Maximum number of retry attempts
        """
        self.api_url = api_url
        self.api_key = api_key
        self.max_retries = max_retries
        self.request_count = 0
    
    def _exponential_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay.
        
        Args:
            attempt: Current attempt number (0-indexed)
        
        Returns:
            Delay in seconds
        """
        base_delay = 1.5
        return base_delay * (2 ** attempt)
    
    def _make_request(self, endpoint: str, payload: dict, timeout: int = 50) -> str:
        """Make HTTP request with exponential backoff retry logic.
        
        Args:
            endpoint: API endpoint path
            payload: Request payload
            timeout: Request timeout in seconds
        
        Returns:
            API response text or error message
        """
        auth_header = f"Bearer {self.api_key}"
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json"
        }
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.api_url}{endpoint}",
                    json=payload,
                    headers=headers,
                    timeout=timeout
                )
                self.request_count += 1
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("result", "")
                
                if response.status_code in [500, 502, 503, 504]:
                    last_error = f"Erreur serveur {response.status_code}"
                    if attempt < self.max_retries - 1:
                        delay = self._exponential_backoff(attempt)
                        logger.warning(f"  {last_error}. Nouvelle tentative dans {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                
                return f"Erreur API: {response.status_code} - {response.text[:100]}"
                
            except requests.exceptions.Timeout:
                last_error = "Délai d'attente dépassé"
                if attempt < self.max_retries - 1:
                    delay = self._exponential_backoff(attempt)
                    logger.warning(f"  {last_error}. Nouvelle tentative dans {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                    
            except requests.exceptions.RequestException as e:
                last_error = f"Requête échouée: {str(e)}"
                if attempt < self.max_retries - 1:
                    delay = self._exponential_backoff(attempt)
                    logger.warning(f"  {last_error}. Nouvelle tentative dans {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                    
            except Exception as e:
                last_error = f"Erreur inattendue: {str(e)}"
                logger.error(f"  {last_error}")
                break
        
        return f"Requête échouée après {self.max_retries} tentatives: {last_error}"
    
    def call_vision_api(self, image_b64: str, prompt: str, model: str) -> str:
        """Call the /process-pdf endpoint for vision queries.
        
        Args:
            image_b64: Base64 encoded image
            prompt: Text prompt
            model: AI model to use
        
        Returns:
            API response text
        """
        payload = {
            "pdfPage": image_b64,
            "prompt": prompt,
            "model": model
        }
        
        return self._make_request("/process-pdf", payload, timeout=50)
    
    def call_text_api(self, query: str, model: str) -> str:
        """Call the /ask endpoint for text-only queries.
        
        Args:
            query: Text query
            model: AI model to use
        
        Returns:
            API response text
        """
        payload = {
            "query": query,
            "model": model
        }
        
        return self._make_request("/ask", payload, timeout=50)
    
    @staticmethod
    def parse_json_response(response_text: str) -> Optional[dict]:
        """Parse and validate JSON from API response with schema validation.
        
        Uses a multi-stage extraction and validation approach:
        1. Direct JSON parsing
        2. Code block extraction
        3. Bracket-based extraction
        4. Schema validation
        5. Error recovery
        
        Args:
            response_text: Raw API response
        
        Returns:
            Validated JSON dict or None
        """
        import json
        
        if not response_text or not response_text.strip():
            logger.warning("  Réponse vide reçue")
            return None
        
        candidate = APIClient._attempt_direct_parse(response_text)
        if candidate:
            validated = APIClient._validate_schema(candidate)
            if validated:
                return validated
        
        candidate = APIClient._extract_from_code_blocks(response_text)
        if candidate:
            validated = APIClient._validate_schema(candidate)
            if validated:
                return validated
        
        candidate = APIClient._extract_by_brackets(response_text)
        if candidate:
            validated = APIClient._validate_schema(candidate)
            if validated:
                return validated
        
        recovered = APIClient._attempt_recovery(response_text)
        if recovered:
            validated = APIClient._validate_schema(recovered)
            if validated:
                logger.info("  JSON récupéré après réparation")
                return validated
        
        logger.error("  Toutes les méthodes d'extraction JSON ont échoué")
        return None
    
    @staticmethod
    def _attempt_direct_parse(text: str) -> Optional[dict]:
        """Attempt direct JSON parsing."""
        import json
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None
    
    @staticmethod
    def _extract_from_code_blocks(text: str) -> Optional[dict]:
        """Extract JSON from markdown code blocks."""
        import json
        import re
        
        patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
            r'`(\{.*?\})`'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    return json.loads(match)
                except (json.JSONDecodeError, ValueError):
                    continue
        
        return None
    
    @staticmethod
    def _extract_by_brackets(text: str) -> Optional[dict]:
        """Extract JSON by finding balanced brackets."""
        import json
        
        start_idx = text.find('{')
        if start_idx == -1:
            return None
        
        bracket_count = 0
        in_string = False
        escape_next = False
        
        for i in range(start_idx, len(text)):
            char = text[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"':
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    bracket_count += 1
                elif char == '}':
                    bracket_count -= 1
                    if bracket_count == 0:
                        json_str = text[start_idx:i+1]
                        try:
                            return json.loads(json_str)
                        except (json.JSONDecodeError, ValueError):
                            return None
        
        return None
    
    @staticmethod
    def _attempt_recovery(text: str) -> Optional[dict]:
        """Attempt to recover malformed JSON."""
        import json
        import re
        
        fixes = [
            (r',\s*}', '}'),
            (r',\s*]', ']'),
            (r"'([^']*)':", r'"\1":'),
            (r'//.*?\n', '\n'),
            (r'/\*.*?\*/', ''),
        ]
        
        cleaned = text
        for pattern, replacement in fixes:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.DOTALL)
        
        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            pass
        
        return APIClient._extract_by_brackets(cleaned)
    
    @staticmethod
    def _validate_schema(data: dict) -> Optional[dict]:
        """Validate JSON structure matches expected schema.
        
        Expected schema:
        {
            "sections": [
                {"name": str, "startPage": int, "endPage": int}
            ]
        }
        
        Args:
            data: Parsed JSON data
        
        Returns:
            Validated data or None if invalid
        """
        if not isinstance(data, dict):
            logger.warning("  Validation du schéma échouée: pas un dictionnaire")
            return None
        
        if "sections" not in data:
            logger.warning("  Validation du schéma échouée: clé 'sections' manquante")
            return None
        
        sections = data["sections"]
        if not isinstance(sections, list):
            logger.warning("  Validation du schéma échouée: 'sections' n'est pas une liste")
            return None
        
        validated_sections = []
        for idx, section in enumerate(sections):
            if not isinstance(section, dict):
                logger.warning(f"  Section {idx} n'est pas un dictionnaire, ignorée")
                continue
            
            if "name" not in section or "startPage" not in section or "endPage" not in section:
                logger.warning(f"  Section {idx} champs requis manquants, ignorée")
                continue
            
            try:
                name = str(section["name"])
                start_page = int(section["startPage"])
                end_page = int(section["endPage"])
                
                if start_page < 1:
                    logger.warning(f"  Section '{name}' a une startPage invalide {start_page}, ignorée")
                    continue
                
                if end_page < start_page:
                    logger.warning(f"  Section '{name}' a endPage < startPage, ignorée")
                    continue
                
                validated_sections.append({
                    "name": name,
                    "startPage": start_page,
                    "endPage": end_page
                })
                
            except (ValueError, TypeError) as e:
                logger.warning(f"  Section {idx} a des types de champs invalides: {e}, ignorée")
                continue
        
        if not validated_sections:
            logger.warning("  Aucune section valide trouvée après validation")
            return None
        
        return {"sections": validated_sections}
