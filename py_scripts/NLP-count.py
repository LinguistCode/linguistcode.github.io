### ---------------------
# SCounts tokens, types, Uber index for a folder, but tokenised by spaCy instead of a regex 
# --> contractions split properly ("don't" = do + n't), closer to what Sketch Engine counts.
### ---------------------

import spacy
import math
import json
from pathlib import Path

def analyser_corpus_nlp(dossier, chemin_sortie_json):
    ### ---------------------
    # LOAD SPACY
    ### ---------------------
    print("Chargement du modèle linguistique spaCy en cours...")
    # English small model. Parser + NER switched off: I only need the tokens,
    # and without them the run is MUCH faster.
    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
    
    chemin = Path(dossier)
    
    # Stop right away if the folder path is wrong.
    if not chemin.exists() or not chemin.is_dir():
        print(f"Erreur : Le dossier '{dossier}' n'existe pas.")
        return

    total_tokens = 0
    types_uniques = set()
    
    ### rglob -> also the .txt files in subfolders.
    fichiers_txt = list(chemin.rglob('*.txt'))
    print(f"Analyse NLP de {len(fichiers_txt)} fichier(s) en cours...\n")

    ### ---------------------
    # FILE LOOP
    ### ---------------------
    for index, fichier in enumerate(fichiers_txt, 1):
        # Progress line every 50 files.
        if index % 50 == 0:
            print(f"Progression : {index} / {len(fichiers_txt)} fichiers analysés...")
            
        try:
            with open(fichier, 'r', encoding='utf-8') as f:
                contenu = f.read()
                
                # spaCy refuses texts over 1M characters by default ->
                # limit raised to 2M for the very long speeches (costs RAM).
                nlp.max_length = 2000000 
                doc = nlp(contenu)
                
                for token in doc:
                    # is_alpha = letters only -> punctuation, digits and spaces are left out.
                    if token.is_alpha:
                        total_tokens += 1
                        # Types counted in lowercase.
                        types_uniques.add(token.text.lower())
                
        except UnicodeDecodeError:
            print(f"Fichier ignoré (problème d'encodage) : {fichier.name}")
        except Exception as e:
            print(f"Erreur lors de la lecture de {fichier.name} : {e}")

    nombre_types = len(types_uniques)
    uber_index = None

    ### ---------------------
    # UBER INDEX (natural log)
    ### ---------------------
    # Only if there is data, otherwise log(0) crashes.
    if total_tokens > 0 and nombre_types > 0:
        log_n = math.log(total_tokens)
        log_v = math.log(nombre_types)
        
        if log_n != log_v:
            uber_index = (log_n ** 2) / (log_n - log_v)
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
            json.dump(resultats, f_json, indent=4, ensure_ascii=False)
    except Exception as e:
         print(f"Erreur lors de la sauvegarde du fichier JSON : {e}")

    ### ---------------------
    # CONSOLE SUMMARY
    ### ---------------------
    print("\n=== RÉSULTATS DE L'ANALYSE NLP ===")
    print(f"Tokens : {total_tokens:,}".replace(',', ' '))
    print(f"Types  : {nombre_types:,}".replace(',', ' '))
    if uber_index:
        print(f"Uber Index : {uber_index}")
    
    print(f"\nLes résultats ont été sauvegardés dans : {chemin_sortie_json}")

### ---------------------
# CONFIG
### ---------------------
# One run per president folder.
dossier_cible = r"D:\path" 
fichier_json = r"D:\path"

analyser_corpus_nlp(dossier_cible, fichier_json)