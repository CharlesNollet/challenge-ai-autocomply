from ast import literal_eval
import json

import requests
import fitz
import base64


API_KEY = "sk-ac-7f8e9d2c4b1a6e5f3d8c7b9a2e4f6d1c"
API_URL = "https://ai-models.autocomply.ca"
MODEL = "gemini-2.5-flash"

listSec = (
        ("Articles & Amendments", "Statuts et Amendements"),
        ("By Laws", "Règlements"),
        ("Unanimous Shareholder Agreement", "Convention Unanime d'Actionnaires"),
        ("Minutes & Resolutions", "Procès-verbaux et Résolutions"),
        ("Directors Register", "Registre des Administrateurs"),
        ("Officers Register", "Registre des Dirigeants"),
        ("Shareholder Register", "Registre des Actionnaires"),
        ("Securities Register", "Registre des Valeurs Mobilières"),
        ("Share Certificates", "Certificats d'Actions"),
        ("Ultimate Beneficial Owner Register", "Registre des Particuliers Ayant un Contrôle Important")
    )

def pdf_page_to_image(doc: fitz.Document, index: int, img= "page.png"):
    """Transforme un page donnée du doc en image.
    @param doc: le document pdf
    @param index: l'index de la page à transformer
    @param img: le nom du fichier image de sortie"""

    page = doc[index]
    zoom = 2
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix)
    pix.save(img)
    
    return img

def secIdentify(img_path: str) -> str:
    """Identifie la section sur laquelle on se trouve.
    @param page: la page sur laquelle on est
    @param listSec: la liste des sections recherchées
    
    Retourne un tuple (bool, str):
    tuple[0] (bool): True si la section est recherchée sinon False
    tuple[1] (str): la section en question"""

    with open(img_path, "rb") as f:
        img = base64.b64encode(f.read()).decode("utf-8")

    prompt = """
Analyse cette image de page PDF. 
Identifie le titre exact de cette section (majoritairement en en-tête) conformémant à cette liste : 
listSec = (
        ("Articles & Amendments", "Statuts et Amendements"),
        ("By Laws", "Règlements"),
        ("Unanimous Shareholder Agreement", "Convention Unanime d'Actionnaires"),
        ("Minutes & Resolutions", "Procès-verbaux et Résolutions"),
        ("Directors Register", "Registre des Administrateurs"),
        ("Officers Register", "Registre des Dirigeants"),
        ("Shareholder Register", "Registre des Actionnaires"),
        ("Securities Register", "Registre des Valeurs Mobilières"),
        ("Share Certificates", "Certificats d'Actions"),
        ("Ultimate Beneficial Owner Register", "Registre des Particuliers Ayant un Contrôle Important")
    )
Ne retourne qu’un objet JSON de la forme {"section": "Nom"}.

Si une section du document correspond à une des sections possibles (en français ou en anglais), retourne le nom exact de la section en anglais.

Si aucune section ne correspond, retourne {"section": "non identifié"}.

Le JSON doit être valide pour ast.literal_eval de Python 3.13.

Aucun texte supplémentaire ni formatage Markdown ne doit être ajouté, seulement le JSON.
"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "pdfPage": img,
        "prompt": prompt
    }
    
    # Envoyer la requête
    response = requests.post(
        f"{API_URL}/process-pdf",
        json=payload,
        headers=headers
    )
    
    if response.status_code == 200:
        try:
            print(response.json())
            result  = literal_eval(response.json()["result"])
            section = str(result["section"]) 
            section = section.title()
        except:
            return secIdentify(img_path)

        if section == "Non Identifié":
            return secIdentify(img_path)
        else:
            return section
    
    

def secResearched(section: str, liste = listSec) -> bool:
    return any(section in a for a in liste)

def searchStartPage(doc: fitz.Document, sec: str, start: int, end: int) -> int:
    """Retourne le numéro de page de début de la section en cours
    @param sec: la section en cours
    @param start: la page de debut limite
    @param end: la page de fin limite"""

    mid = (start + end)//2

    if end - start == 1:
        if secIdentify(pdf_page_to_image(doc, start)) == sec:
            return start
        return end
    elif secIdentify(pdf_page_to_image(doc, mid-1)) == sec:
        return searchStartPage(doc, sec, start, mid-1)
    elif secIdentify(pdf_page_to_image(doc, mid-1)) != sec:
        if secIdentify(pdf_page_to_image(doc, mid)) == sec:
            return mid
        return searchStartPage(doc, sec, mid, end)
    else:
        return 0

def searchEndPage(doc: fitz.Document, sec: str, start: int, end: int) -> int:
    """Retourne le numéro de page de début de la section en cours
    @param sec: la section en cours
    @param start: la page de debut limite
    @param end: la page de fin limite"""

    mid = (start + end)//2

    if end - start == 1:
        if secIdentify(pdf_page_to_image(doc, end)) == sec:
            return end
        return start
    elif secIdentify(pdf_page_to_image(doc, mid-1)) == sec:
        return searchStartPage(doc, sec, mid, end)
    elif secIdentify(pdf_page_to_image(doc, mid+1)) != sec:
        if secIdentify(pdf_page_to_image(doc, mid)) == sec:
            return mid
        return searchStartPage(doc, sec, start, mid)
    else:
        return 0

def extract_sections(filepath) -> list[dict]:

    doc = fitz.open(filepath) # document
    nbre_pages = len(doc)

    sections =  [] # rendu

    page = 0

    while page < nbre_pages:

        section_actuelle = secIdentify(pdf_page_to_image(doc, page))

        if secResearched(section_actuelle):
            assert section_actuelle is not None
            nom_section = section_actuelle

            startpage = page

            page_sup = page

            while page_sup < nbre_pages and secIdentify(pdf_page_to_image(doc, page_sup)) == nom_section:
                page_sup += 10
            
            endpage = searchEndPage(doc, nom_section, page, min(page_sup, nbre_pages))

            sections.append(
                {
                "name": nom_section,
                "startpage": startpage,
                "endpage": endpage
                }
            )
            page = endpage + 1

        else:

            page_sup = page + 10

            while page_sup < nbre_pages:

                section_possible = secIdentify(pdf_page_to_image(doc, page_sup))

                if secResearched(section_possible):
                    break

                page_sup += 10

            if page_sup > nbre_pages:
                break

            nom_section = secIdentify(pdf_page_to_image(doc, page_sup))

            startpage: int = searchStartPage(doc, nom_section, max(1, page_sup - 20), page_sup)

            page_sup: int = startpage

            while page_sup < nbre_pages and secIdentify(pdf_page_to_image(doc, page_sup)) == nom_section:

                page_sup += 10
            
            endpage: int = searchEndPage(doc, nom_section, page_sup - 20, min(page_sup, nbre_pages))

            sections.append(
                {
                "name": nom_section,
                "startpage": startpage,
                "endpage": endpage
                }
            )

            page = endpage + 1
            
            continue

    for section in sections:
        for i in range(len(listSec)):

            if section['name'] in listSec[i]:
                section['name'] = listSec[i][0]
    
    return sections


if __name__ == "__main__":
    import os.path
    from pathlib import Path
    filepath = Path(os.path.dirname(__file__)) / "DEMO_MinuteBook_FR.pdf"

    with open("result.json", "w") as file:
        json.dump(extract_sections(filepath), file, indent=2)
