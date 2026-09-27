### ---------------------
# Corpus profile: tokens, types and Uber index for a whole folder of speeches.
# Regex tokenisation (fast, no dependency). NLP-count.py is the spaCy version of the same thing 
# ---> compare both outputs before quoting any figure.
### ---------------------

import re
import math
import json
from pathlib import Path

def analyser_corpus(dossier, chemin_sortie_json):
    chemin = Path(dossier)
    
    # Stop right away if the folder path is wrong.
    if not chemin.exists() or not chemin.is_dir():
        print(f"Erreur : Le dossier '{dossier}' n'existe pas.")
        return

    total_tokens = 0
    types_uniques = set()
    
    # Words = runs of letters only (accented letters included). Digits and
    # punctuation are dropped, so "9/11" gives nothing here.
    regex_mots = re.compile(r'[a-zA-ZÀ-ÿ]+')

    # rglob -> also picks up the .txt files sitting in subfolders (years).
    fichiers_txt = list(chemin.rglob('*.txt'))
    print(f"Analyse de {len(fichiers_txt)} fichier(s) en cours...\n")

    for index, fichier in enumerate(fichiers_txt, 1):
        # Progress line every 50 files only, otherwise the console gets flooded.
        if index % 50 == 0:
            print(f"Progression : {index} / {len(fichiers_txt)} fichiers analysés...")
            
        try:
            with open(fichier, 'r', encoding='utf-8') as f:
                # Lowercase BEFORE counting, so "Fear" and "fear" = one type.
                contenu = f.read().lower() 
                
                mots = regex_mots.findall(contenu)
                
                total_tokens += len(mots)
                types_uniques.update(mots)
                
        except UnicodeDecodeError:
            print(f"Fichier ignoré (problème d'encodage) : {fichier.name}")
        except Exception as e:
            print(f"Erreur lors de la lecture de {fichier.name} : {e}")

    nombre_types = len(types_uniques)
    uber_index = None

    ### ---------------------
    # UBER INDEX
    ### ---------------------
    # U = (log N)^2 / (log N - log V), natural log. Only if there is data.
    if total_tokens > 0 and nombre_types > 0:
        log_n = math.log(total_tokens)
        log_v = math.log(nombre_types)
        
        ### If tokens == types the denominator is 0 -> skip instead of crashing.
        if log_n != log_v:
            uber_index = (log_n ** 2) / (log_n - log_v)
            ### 4 decimals is plenty for the tables in the thesis.
            uber_index = round(uber_index, 4) 
        else:
            print("Avertissement : Le nombre de types est égal au nombre de tokens.")

    ### ---------------------
    # JSON EXPORT
    ### ---------------------
    resultats = {
        "dossier_analyse": str(chemin.resolve()),
        "fichiers_traites": len(fichiers_txt),
        "total_tokens": total_tokens,
        "total_types": nombre_types,
        "uber_index": uber_index
    }

    try:
        with open(chemin_sortie_json, 'w', encoding='utf-8') as f_json:
            ### indent=4 so the file stays readable by hand.
            json.dump(resultats, f_json, indent=4, ensure_ascii=False)
    except Exception as e:
         print(f"Erreur lors de la sauvegarde du fichier JSON : {e}")

    ### ---------------------
    # CONSOLE SUMMARY
    ### ---------------------
    print("=== RÉSULTATS DE L'ANALYSE ===")
    print(f"Tokens : {total_tokens:,}".replace(',', ' '))
    print(f"Types  : {nombre_types:,}".replace(',', ' '))
    if uber_index:
        print(f"Uber Index : {uber_index}")
    
    print(f"\nLes résultats ont été sauvegardés dans : {chemin_sortie_json}")

### ---------------------
# CONFIG
### ---------------------
dossier_cible = r"path" 
fichier_json = r"path"

analyser_corpus(dossier_cible, fichier_json)