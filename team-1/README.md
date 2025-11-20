**Équipe : 1**

Nous sommes une équipe composé de Olivier Hamel (Info 2e année) et Raphaël Grou (Log 2e année).
On ne s'est pas inscrit sur le site de la scav.


**Dépendance :**
 - `pip install -r solution/requirements.txt`

**Clé API :**
 - Remplacer la clé API dans `config.py` ou dans la terminale : 

        set AUTOCOMPLY_API_KEY=VOTRE_CLE 
        OU
        $env:AUTOCOMPLY_API_KEY="VOTRE_CLE"

**Pour executer :**
 - `python -m solution.cli votre_minute_book.pdf`


**Voici la solution que nous avons implémenté :** 

- Extraction texte: `PyMuPDF` lit le texte de chaque page.
- Score qualité OCR: `solution/ocr_quality.py` calcule une note (0–100) via:
  - ratio alphanumérique, longueur, voyelles, caractères corrompus, détection langue (EN/FR).
  - Si note < `OCR_QUALITY_THRESHOLD` → page marquée pour vision (`/process-pdf`).

- Déclencheurs Vision:
  - `isTextIncoherent` renvoyé par le LLM texte,
  - Score OCR trop bas,
  - Confiance texte < `VISION_LOW_CONFIDENCE`.

- Itérations:
  - Pass 1: uniquement `/ask` sur des blocs texte de plusieurs pages (avec contexte des pages avant et après).
  - Tout les blocs sont envoyer en parralèle sur différent thread.
  - Pass 2+:
    - Séparation en deux files:
      - Blocs “VISION”: 1 page par bloc, uniquement `/process-pdf`.
      - Blocs “ASK”: pages restantes regroupées par label courant (exclusion des pages vision).
        - On envoie les pages avant et après le Bloc pour ajouter du context supplémentaire.
    - Une page devient “finale” dès que `confidence >= CONFIDENCE_FINAL_THRESHOLD`.
    - On s’arrête dès que toutes les pages sont finales ou que `MAX_ITERATIONS` est atteint.
