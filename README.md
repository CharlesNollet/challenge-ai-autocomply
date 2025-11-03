# Challenge de Découpage de PDF - AutoComply

## 🎯 Objectif du Challenge

Votre mission est de développer une fonction de **découpage de PDF** (PDF splitter) qui analyse un registre des procès-verbaux (minute book) et identifie automatiquement les différentes sections du document.

### Le Défi

Vous recevrez un PDF contenant un registre des procès-verbaux avec plusieurs sections. Votre objectif est de retourner, pour chaque section, la **page de début** et la **page de fin**.

**📖 Qu'est-ce qu'un Registre des Procès-verbaux (Minute Book) ?**

Un **registre des procès-verbaux** (Minute Book) est un document juridique essentiel qui contient l'ensemble des documents corporatifs et des décisions importantes d'une entreprise. Il sert de registre officiel et historique de toutes les activités de gouvernance de la société. Ces registres sont cruciaux pour la conformité légale, la gouvernance d'entreprise, la traçabilité, les transactions financières et les audits. Traditionnellement maintenus sous forme papier, ils sont de plus en plus numérisés en PDF, d'où le besoin d'automatiser leur traitement et leur organisation. 

**Contraintes importantes :**
- Les sections ont des longueurs variables
- Les sections peuvent apparaître dans n'importe quel ordre
- Les sections sont **contiguës** (pas de pages manquantes entre le début et la fin d'une section)
- Vous devez **minimiser le nombre de requêtes** à l'API en inférant intelligemment les pages
- Vous devez **minimiser les erreurs** dans la détection des sections
- Vous devez **optimiser le temps d'exécution**

### Sections à Identifier

Vous devez identifier les sections suivantes dans le registre des procès-verbaux. **Note importante : toutes les sections ne sont pas nécessairement présentes dans chaque document.**

1. **Articles and Amendments** / **Statuts et Amendements**
2. **By Laws** / **Règlements**
3. **Unanimous Shareholder Agreement** / **Convention d'Actionnaires Unanime**
4. **Minutes and Resolutions** / **Procès-verbaux et Résolutions**
5. **Directors Register** / **Registre des Administrateurs**
6. **Officers Register** / **Registre des Dirigeants**
7. **Shareholder Register** / **Registre des Actionnaires**
8. **Securities Register** / **Registre des Titres**
9. **Share Certificates** / **Certificats d'Actions**
10. **Ultimate Beneficial Owner Register** / **Registre des Bénéficiaires Ultimes**

Votre solution doit être capable de détecter ces sections même si elles apparaissent dans un ordre différent ou si certaines sont absentes du document.

### Système de Notation

Votre score final sera calculé selon la formule suivante :

```
Score = Temps d'exécution (secondes) × Nombre de requêtes API × Nombre d'erreurs
```

**L'équipe avec le score le plus bas gagne !** 🏆

Votre code sera testé sur un registre des procès-verbaux que vous n'aurez pas vu auparavant. Assurez-vous que votre solution soit robuste et généralisable.

### Langage de Programmation

Vous êtes libre de choisir le langage de programmation de votre choix. Nous recommandons **TypeScript** ou **Python** pour faciliter l'intégration avec l'API.

---

## 📡 Accès à l'API

L'API est disponible à l'adresse suivante :

**URL de base :** `https://ai-models.autocomply.ca`

### Authentification

Toutes les requêtes nécessitent une clé API dans l'en-tête `Authorization` :

```
Authorization: Bearer sk-ac-7f8e9d2c4b1a6e5f3d8c7b9a2e4f6d1c
```

---

## 🔌 Documentation de l'API

### Endpoint : POST `/process-pdf`

Cet endpoint permet de traiter une page de PDF en l'envoyant à un modèle d'IA visionnaire.

**URL complète :** `https://ai-models.autocomply.ca/process-pdf`

**En-têtes requis :**
```
Authorization: Bearer sk-ac-7f8e9d2c4b1a6e5f3d8c7b9a2e4f6d1c
Content-Type: application/json
```

**Corps de la requête :**
```json
{
  "pdfPage": "base64_encoded_image_string",
  "prompt": "Votre prompt ici"
}
```

**Réponse en cas de succès (200) :**
```json
{
  "result": "Réponse textuelle du modèle IA"
}
```

**Réponse en cas d'erreur (401) :**
```json
{
  "error": "Unauthorized",
  "message": "Valid API key required in Authorization header (Bearer <api-key>)"
}
```

### Endpoint : GET `/health`

Vérification de l'état de l'API (sans authentification).

**URL complète :** `https://ai-models.autocomply.ca/health`

**Réponse :**
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

---

## 💡 Exemple d'Utilisation

### Python avec `requests`

```python
import requests
import base64
from pathlib import Path

# Configuration
API_URL = "https://ai-models.autocomply.ca"
API_KEY = "sk-ac-7f8e9d2c4b1a6e5f3d8c7b9a2e4f6d1c"

# Convertir une page PDF en image (base64)
# Note: Vous devrez utiliser une bibliothèque comme PyMuPDF ou pdf2image
def pdf_page_to_base64(pdf_path, page_number):
    # Exemple avec PyMuPDF
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom
    img_bytes = pix.tobytes("png")
    doc.close()
    return base64.b64encode(img_bytes).decode('utf-8')

# Traiter une page
def process_page(pdf_path, page_number, prompt):
    # Convertir la page en base64
    page_b64 = pdf_page_to_base64(pdf_path, page_number)
    
    # Préparer la requête
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "pdfPage": page_b64,
        "prompt": prompt
    }
    
    # Envoyer la requête
    response = requests.post(
        f"{API_URL}/process-pdf",
        json=payload,
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()["result"]
    else:
        print(f"Erreur: {response.status_code} - {response.text}")
        return None

# Exemple d'utilisation
if __name__ == "__main__":
    # Vérifier que l'API est accessible
    health_response = requests.get(f"{API_URL}/health")
    print(f"API Status: {health_response.json()}")
    
    # Traiter la première page
    result = process_page(
        "minute_book.pdf",
        page_number=0,
        prompt="Quel est le titre de cette section ? Identifie également si c'est le début ou la fin d'une section."
    )
    
    print(f"Résultat: {result}")
```

---

## 🎓 Stratégies Recommandées

### 1. Minimiser le Nombre de Requêtes

- **Échantillonnage intelligent** : Ne traitez pas toutes les pages. Utilisez une stratégie d'échantillonnage (par exemple, toutes les 2-3 pages) pour identifier les sections
- **Détection de motifs** : Si vous identifiez un pattern dans les sections (par exemple, les titres de sections ont un format spécifique), vous pouvez inférer les limites sans traiter toutes les pages
- **Recherche binaire** : Utilisez une approche de recherche binaire pour trouver rapidement les limites des sections

### 2. Minimiser les Erreurs

- **Validation croisée** : Vérifiez les résultats en traitant quelques pages supplémentaires autour des limites détectées
- **Analyse contextuelle** : Utilisez des prompts intelligents qui demandent au modèle d'identifier non seulement la section actuelle, mais aussi les indices de début/fin
- **Vérification de cohérence** : Assurez-vous que les sections détectées sont cohérentes (par exemple, pas de chevauchement)
- **Gestion des pages à faible contexte** : Certaines pages, lorsqu'analysées isolément, peuvent contenir très peu d'informations utiles (par exemple, une page de signatures sans la page précédente qui contient le contenu). Dans ces cas, les réponses du modèle IA peuvent être peu fiables. **Utilisez des niveaux de confiance** dans vos prompts pour demander au modèle d'évaluer sa certitude, et catégorisez les résultats en fonction de ces niveaux de confiance. Si une page a un faible niveau de confiance, considérez de traiter les pages adjacentes pour obtenir plus de contexte avant de prendre une décision.

### 3. Optimiser le Temps d'Exécution

- **Traitement parallèle** : Si vous devez traiter plusieurs pages, faites-le en parallèle (avec des limites raisonnables pour ne pas surcharger l'API)
- **Mise en cache** : Si vous traitez les mêmes pages plusieurs fois, mettez en cache les résultats
- **Optimisation des images** : Réduisez la résolution des images si possible (tout en gardant une qualité suffisante pour l'IA)

### 4. Format de Sortie Attendu

Votre fonction doit retourner une liste de sections avec leurs pages de début et de fin. Format suggéré :

```json
{
  "sections": [
    {
      "name": "Articles and Amendments",
      "startPage": 1,
      "endPage": 5
    },
    {
      "name": "Shareholder Register",
      "startPage": 6,
      "endPage": 12
    }
  ]
}
```

**⚠️ IMPORTANT - Noms des Sections :**

- Le nom de chaque section (`name`) doit être **en anglais**, **exactement tel qu'il apparaît au début de la section dans le document**
- Les noms doivent correspondre exactement à l'une des 10 sections listées précédemment (voir section "Sections à Identifier")
- **Toute faute de frappe, variation d'orthographe ou nom similaire mais incorrect sera rejeté par le correcteur automatique**
- Assurez-vous d'extraire le nom exact tel qu'il est écrit dans le document, sans modification
- Exemples de noms corrects : `"Articles and Amendments"`, `"By Laws"`, `"Shareholder Register"`
- Exemples qui seraient rejetés : `"Article and Amendment"` (singulier), `"By-Laws"` (avec tiret), `"Shareholders Register"` (pluriel incorrect)

---

## 📚 Bibliothèques Utiles

### Python
- `PyMuPDF` (fitz) : Conversion PDF → images
- `pdf2image` : Alternative pour la conversion
- `requests` : Requêtes HTTP
- `PIL` (Pillow) : Manipulation d'images

### TypeScript/Node.js
- `pdf-lib` : Manipulation de PDF
- `pdfjs-dist` : Alternative pour la lecture de PDF
- `canvas` : Conversion PDF → images
- `node-fetch` ou `axios` : Requêtes HTTP

---

## ⚠️ Notes Importantes

1. **Rate Limiting** : Faites attention à ne pas surcharger l'API. Implémentez un système de retry avec backoff exponentiel en cas d'erreur.

2. **Qualité des Images** : Les images doivent être en format PNG ou JPEG, encodées en base64. Une résolution de 150-300 DPI est généralement suffisante.

3. **Prompts Efficaces** : Créez des prompts clairs et spécifiques pour obtenir les meilleurs résultats du modèle IA.

4. **Gestion des Erreurs** : Gérez gracieusement les erreurs réseau et les erreurs de l'API.

5. **Test avec Votre PDF** : Testez votre solution avec le PDF fourni avant la soumission finale.

---

## 📤 Soumission

**⚠️ IMPORTANT - Soumission de votre Solution :**

Pour participer au challenge, vous devez soumettre votre solution en créant une **pull request** vers ce dépôt **avant la fin du concours**.

**Instructions de soumission :**

1. Créez un dossier avec le **nom de votre équipe** (utilisez uniquement des caractères alphanumériques et des tirets, pas d'espaces)
2. Placez votre code dans ce dossier
3. Créez une **pull request** vers ce dépôt avec votre solution
4. Assurez-vous que votre pull request est créée **avant la date limite du concours**

**Exemple de structure :**
```
challenge-ai-autocomply/
  ├── README.md
  ├── team-alpha/
  │   ├── solution.py
  │   └── requirements.txt
  ├── team-beta/
  │   ├── solution.ts
  │   └── package.json
  └── ...
```

Les soumissions qui ne respectent pas ces instructions ne seront pas évaluées.

---

## 🚀 Bonne Chance !

N'oubliez pas : le score est calculé comme **Temps × Requêtes × Erreurs**. Trouvez le bon équilibre entre précision et efficacité !

Les membres de l'équipe gagnante se mériteront une entrevue afin d'obtenir un stage d'été chez AutoComply.

Si vous avez des questions pendant le concours, n'hésitez pas à demander aux organisateurs.


