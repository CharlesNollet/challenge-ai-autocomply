from __future__ import annotations

import os
from textwrap import dedent

# API configuration
API_URL = os.getenv("AUTOCOMPLY_API_URL", "https://ai-models.autocomply.ca")
API_KEY = os.getenv("AUTOCOMPLY_API_KEY", "sk-ac-7f8e9d2c4b1a6e5f3d8c7b9a2e4f6d1c")
DEFAULT_MODEL = os.getenv("AUTOCOMPLY_MODEL", "gemini-2.5-flash")
DEBUG_LOG_PATH = os.getenv("DEBUG_LOG_PATH")

# Strategy parameters
BLOCK_SIZE = int(os.getenv("BLOCK_SIZE", "55"))
CONTEXT_PAGES = int(os.getenv("CONTEXT_PAGES", "3"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))
CONFIDENCE_FINAL_THRESHOLD = float(os.getenv("CONFIDENCE_FINAL_THRESHOLD", "85.0"))
MAX_PARALLEL_REQUESTS = int(os.getenv("MAX_PARALLEL_REQUESTS", "4"))

# Vision fallback
VISION_FALLBACK_ENABLED = os.getenv("VISION_FALLBACK_ENABLED", "1").lower() not in ("0", "false", "no")
OCR_QUALITY_THRESHOLD = float(os.getenv("OCR_QUALITY_THRESHOLD", "35.0"))
VISION_LOW_CONFIDENCE = float(os.getenv("VISION_LOW_CONFIDENCE", "80.0"))
VISION_MAX_PAGES = int(os.getenv("VISION_MAX_PAGES", "40"))
VISION_MODEL = os.getenv("VISION_MODEL", DEFAULT_MODEL)

ALLOWED_LABELS = [
    "Articles & Amendments",
    "By Laws",
    "Unanimous Shareholder Agreement",
    "Minutes & Resolutions",
    "Directors Register",
    "Officers Register",
    "Shareholder Register",
    "Securities Register",
    "Share Certificates",
    "Ultimate Beneficial Owner Register",
]

CLASSIFICATION_PROMPT = dedent(
    """
    You are a classification model for corporate minute books (French and English).

                Your job in each call is:
                - Read a set of pages as ONE continuous document.
                - Use surrounding pages as CONTEXT ONLY.
                - Assign exactly ONE section label and ONE confidence percentage to EACH TARGET PAGE in the block.

                You will receive a JSON object with this structure:

                {
                  "targetInterval": { "startPageIndex": int, "endPageIndex": int },
                  "pages": [
                    {
                      "pageIndex": int,          // 0-based index in the PDF
                      "isTarget": boolean,
                      "isFinal": boolean,
                      "text": string,
                      "finalLabel": string | null
                    },
                    ...
                  ],
                  "allowedLabels": [ "<label1>", "<label2>", ... ]
                }

                - The pages array contains:
                  - ALL target pages in the current block (startPageIndex..endPageIndex).
                  - PLUS at least the page immediately BEFORE the block and the page immediately AFTER the block when they exist, used ONLY as context.
                - You MUST treat the pages in ascending pageIndex order as a single continuous text flow.
                - Only pageIndex values are provided (0-based). If a page in this block has isFinal = true, its finalLabel is confirmed for that page; use it as an anchor, but do NOT assume neighboring pages share the same label.

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

                --------------------------------
                HOW TO USE CONTEXT VS TARGET
                --------------------------------

                - Read every entry in the pages array IN ORDER as one continuous document.
                - Pages with isTarget = false are CONTEXT ONLY. They inform your understanding but must not be labeled.
                - Pages with isTarget = true MUST be labeled now.
                - Blocks can contain multiple sections. Even if a context or target page is finalized, re-evaluate each target page independently; never assume the rest of the block shares that label.

                --------------------------------
                CLASSIFICATION TASK
                --------------------------------

                For each page where isTarget = true:
                1) Choose the single label from allowedLabels that best describes that page's main function.
                   - Transitional pages still get the label covering the most substantial or legally important content.
                2) Assign a confidencePercent between 0 and 100.
                   - 100 = virtually certain. 50 = multiple plausible labels with no clear winner. <40 = highly unsure.
                3) Context pages are never labeled.

                --------------------------------
                OUTPUT FORMAT (STRICT)
                --------------------------------

                Return a single JSON object and NOTHING else (no prose, no comments):

                {
                  "pagePredictions": [
                    {
                      "pageIndex": <int>,              // must match a target page's pageIndex
                      "label": "<one of allowedLabels>",
                      "confidencePercent": <0-100>,
                      "isTextIncoherent": <true|false>   // set true if provided page.text is unreadable/garbled/empty
                    },
                    ...
                  ]
                }

                - For every target page you MUST output a label that exactly matches one of these : "Articles & Amendments", "By Laws", "Unanimous Shareholder Agreement", "Minutes & Resolutions", "Directors Register", "Officers Register", "Shareholder Register", "Securities Register", "Share Certificates", "Ultimate Beneficial Owner Register".
                - Do NOT translate, rephrase, or adjust the spelling/punctuation of these labels.
                - Any label outside that list is invalid.

                Constraints:
                - Include EXACTLY one entry in pagePredictions for each target page (isTarget = true).
                - Do NOT include entries for context pages (isTarget = false).
                - Use labels exactly as provided in allowedLabels (no inventing new labels).
                - Confidence values must be between 0 and 100.
                - If uncertain between labels, pick the most plausible one and lower your confidencePercent accordingly.
    """
).strip()


