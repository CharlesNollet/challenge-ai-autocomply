from __future__ import annotations

import json
from textwrap import dedent
from typing import Dict

import requests

from solution.config import API_KEY, API_URL, DEFAULT_MODEL, ALLOWED_LABELS


class VisionClientError(RuntimeError):
    """Raised when the vision client cannot return a valid JSON result."""


class VisionClient:
    """Minimal client for the /process-pdf endpoint."""

    def __init__(
        self,
        api_url: str = API_URL,
        api_key: str = API_KEY,
        model: str = DEFAULT_MODEL,
        timeout: int = 120,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def classify_page_image(self, page_b64: str) -> Dict:
        """
        Send one page image to the /process-pdf endpoint and parse a strict JSON.
        """
        print("Used image to classify page \n");

        prompt = dedent(
            f"""
            
            --------------------------------
            SECTION LABELS (allowedLabels)
            --------------------------------

            ## 1. 📜 Statuts et Amendements (Articles & Amendments)

            ### Élément distinctif
            - Souvent des documents émis par le gouvernement

            ### Statuts de constitution
            - Catégories d'action
            - Nom de la corporation
            - Numéro d'entreprise
            - Restrictions sur les transferts d'actions
            - Adresse de la société

            ### Statuts de modification
            - Détails sur ce qui a changé
            - Adresse, Nom, Droits
            - Répétition des statuts de constitution mais seulement pour ce qui a été modifié

            ### Statuts de fusion
            - Deux entités ont fusionné
            - Répétition des infos du statut de constitution mais avec les modifications liées à la fusion

            ### Statuts de continuation ou prorogation
            - Entité incorporée qui change de loi (ex. : de Canadienne à Québécoise)

            ---

            ## 2. 📑 By Laws (Règlements)

            - **Entête distinctif** : Entête qui dit "Règlement" ou "By-Law" à la première page
            - Documents qui servent à mettre des règlements internes
            - Paragraphes très souvent numérotés
            - Contenu qui explique des procédures
            - **⚠️ L'entête du document à la première page de cette section est le véritable élément différenciateur**

            ---

            ## 3. 🤝 Convention Unanime d'Actionnaires (Unanimous Shareholder Agreement)

            - Retire les pouvoirs aux administrateurs pour les donner aux actionnaires
            - Contenu qui contrôle les droits et privilèges des actionnaires
            - Signée par tous les actionnaires
            - **⚠️ L'entête du document à la première page de cette section est le véritable élément différenciateur**

            ---

            ## 4. 📝 Minutes et Résolutions (Minutes & Resolutions)

            - La section un peu fourre-tout qui contient beaucoup de documents indépendants
            - La section la plus longue du livre

            ---

            ## 5. 👥 Registre des Administrateurs (Directors Register)

            ### Format
            - Format tableau
            - Entête sur la première page ou toutes les pages

            ### Contenu typique
            - Nom
            - Adresse
            - Date de début
            - Date de fin
            - Résidence (optionnel)

            **💡 Astuce** : Se fier sur le contenu pour identifier cette section

            ---

            ## 6. 💼 Registre des Dirigeants (Officers Register)

            ### Format
            - Format tableau
            - Entête sur la première page ou toutes les pages

            ### Contenu typique
            - Nom
            - Adresse
            - Date de début
            - Date de fin
            - Fonction
            - Résidence (optionnel)

            **💡 Astuce** : Se fier sur le contenu pour identifier cette section

            ---

            ## 7. 📊 Registre des Actionnaires (Shareholder Register)

            ### Format
            - Format tableau
            - Entête sur la première page ou toutes les pages

            ### Contenu typique
            - Nom
            - Adresse
            - Date de début
            - Date de fin
            - Résidence (optionnel)

            **💡 Astuce** : Se fier sur le contenu pour identifier cette section

            ---

            ## 8. 📈 Registre des Valeurs Mobilières (Securities Register)

            ### Format
            - Format tableau

            ### Caractéristiques
            - Page spécifique par actionnaire et catégorie
            - Liste des transactions
            - Transferts

            ---

            ## 9. 🎫 Certificats d'Actions (Share Certificates)

            ### Caractéristiques visuelles
            - Document horizontal
            - Loi applicable
            - Nombre d'actions écrit plusieurs fois sur la page
            - Nom de l'actionnaire écrit plusieurs fois sur la page

            ---

            ## 10. 🏛️ Registre des PACI (Ultimate Beneficial Owner Register)

            ### Format
            - Format tableau
            - Entête
            - Souvent des références aux pourcentages

            Return ONLY this JSON and nothing else:
            {{
              "label": "<one of allowed labels>",
              "confidencePercent": <0-100>
            }}
            """
        ).strip()

        body = {"pdfPage": page_b64, "prompt": prompt, "model": self.model}
        try:
            response = requests.post(
                f"{self.api_url}/process-pdf",
                headers=self._headers,
                json=body,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:  # pragma: no cover - network
            raise VisionClientError(f"Vision request failed: {exc}") from exc
        except ValueError as exc:
            raise VisionClientError("Vision response is not valid JSON") from exc

        raw = data.get("result", "")
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise VisionClientError("Vision result did not include a JSON object")
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError as exc:
            raise VisionClientError(f"Unable to decode vision JSON: {exc}") from exc


