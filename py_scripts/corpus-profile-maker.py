import re
import math
import json
from pathlib import Path

def analyser_corpus(dossier, chemin_sortie_json):
    chemin = Path(dossier)
    
    # Vérifier que le dossier racine existe bien
    if not chemin.exists() or not chemin.is_dir():
        print(f"Erreur : Le dossier '{dossier}' n'existe pas.")
        return

    total_tokens = 0
    types_uniques = set()
    
    # Expression régulière pour extraire uniquement les mots (incluant les accents)
    regex_mots = re.compile(r'[a-zA-ZÀ-ÿ]+')

    # Chercher tous les fichiers .txt dans le dossier et ses sous-dossiers
    fichiers_txt = list(chemin.rglob('*.txt'))
    print(f"Analyse de {len(fichiers_txt)} fichier(s) en cours...\n")

    for index, fichier in enumerate(fichiers_txt, 1):
        # Affiche un message tous les 50 fichiers pour ne pas inonder la console
        if index % 50 == 0:
            print(f"Progression : {index} / {len(fichiers_txt)} fichiers analysés...")
            
        try:
            with open(fichier, 'r', encoding='utf-8') as f:
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

    # ==========================================
    # CALCUL DE L'UBER INDEX
    # ==========================================
    # S'assurer qu'il y a des données pour éviter les erreurs mathématiques
    if total_tokens > 0 and nombre_types > 0:
        log_n = math.log(total_tokens)
        log_v = math.log(nombre_types)
        
        # Éviter la division par zéro (au cas où Tokens == Types)
        if log_n != log_v:
            uber_index = (log_n ** 2) / (log_n - log_v)
            # Arrondir à 4 décimales pour la lisibilité
            uber_index = round(uber_index, 4) 
        else:
            print("Avertissement : Le nombre de types est égal au nombre de tokens.")

    # ==========================================
    # CRÉATION ET SAUVEGARDE DU JSON
    # ==========================================
    resultats = {
        "dossier_analyse": str(chemin.resolve()),
        "fichiers_traites": len(fichiers_txt),
        "total_tokens": total_tokens,
        "total_types": nombre_types,
        "uber_index": uber_index
    }

    try:
        with open(chemin_sortie_json, 'w', encoding='utf-8') as f_json:
            # indent=4 permet de formater le fichier de manière lisible
            json.dump(resultats, f_json, indent=4, ensure_ascii=False)
    except Exception as e:
         print(f"Erreur lors de la sauvegarde du fichier JSON : {e}")

    # ==========================================
    # AFFICHAGE DES RÉSULTATS DANS LA CONSOLE
    # ==========================================
    print("=== RÉSULTATS DE L'ANALYSE ===")
    print(f"Tokens : {total_tokens:,}".replace(',', ' '))
    print(f"Types  : {nombre_types:,}".replace(',', ' '))
    if uber_index:
        print(f"Uber Index : {uber_index}")
    
    print(f"\nLes résultats ont été sauvegardés dans : {chemin_sortie_json}")

# ==========================================
# CONFIGURATION
# ==========================================
dossier_cible = r"D:\Local_corpus\Bush" 
fichier_json = r"D:\Local_corpus\Bush\profil-bush-updated.json"

analyser_corpus(dossier_cible, fichier_json)