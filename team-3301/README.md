# Challenge Autocomply - Team 3301

## Description

Cette solution classifie automatiquement les sections d'un registre corporatif (minute book) en utilisant une approche basée sur l'extraction de texte et l'analyse par IA.

## Contact 

N'hésitez pas à me contacter après 12h si jamais vous avez des questions,
mon discord est le suivant : lx___xl

(C'est moi qui a fait le post Format de remise dans le serveur discord d'autocomply)

J'ai passé toute la nuit sur ce défi, car j'ai passé trop de temps sur les autres défis de la competition.
Les LLM m'ont beaucoup aidé pour ce défi. Mention honorable pour Kiro, et Gemini 3 Pro

Sur ce, je m'en vais dormir et je vais me réveiller (hopefully) à 12h xD

## Installation

```bash
pip install -r requirements.txt
```

Dépendances principales:
- PyMuPDF (fitz)
- Pillow
- requests

## Configuration

1. **Placer le PDF**: Mettez votre fichier PDF dans le dossier `team-3301/`

2. **Configurer le chemin**: Modifiez `config.py` pour pointer vers votre PDF:
```python
MINUTEBOOK_PDF_PATH = "VOTRE_FICHIER.pdf"
```

3. **Clés API**: Les clés API sont déjà configurées dans `config.py`

## Utilisation

```bash
cd team-3301
python main.py
```

Les résultats seront sauvegardés dans `result.json`.

## Technique Utilisée


**1. Extraction de Texte par Lots**
- Le PDF est divisé en lots de 6 pages.
- Chaque lot est converti en grille d'images (2 colonnes)
- L'IA extrait le texte visible de chaque page via vision API
- Traitement parallèle pour optimiser la vitesse

**2. Identification de Structure**
- Le texte agrégé est analysé pour identifier les sections
- Post-traitement pour corriger les chevauchements et combler les écarts

### Points Clés de la Solution

**Contexte Riche dans les Prompts**
- Les prompts contiennent des instructions détaillées et du contexte spécifique
- Liste explicite des types de sections attendues
- Exemples de format de sortie
- Contraintes structurelles (pas de chevauchement, pas d'écart)
- Instructions pour ne pas manquer les sections courtes (registres)

**Robustesse**
- Gestion d'erreurs avec retry automatique (backoff exponentiel)
- Parsing JSON multi-étapes avec récupération d'erreurs
- Validation de schéma stricte
- Correction automatique des frontières de sections

**Performance**
- Traitement parallèle des lots (jusqu'à 10 threads)
- Optimisation des images (compression JPEG, résolution adaptée)
- Cache de polices pour les labels de pages

