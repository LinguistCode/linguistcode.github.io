import spacy
import math
import json
from pathlib import Path

def analyser_corpus_nlp(dossier, chemin_sortie_json):
    # ==========================================
    # INITIALISATION DU MOTEUR NLP
    # ==========================================
    print("Chargement du modèle linguistique spaCy en cours...")
    # Charger le modèle anglais. 
    # Désactiver les modules "parser" et "ner" (analyse syntaxique et entités nommées) 
    # pour accélérer considérablement le traitement, car on veut que les tokens.
    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
    
    chemin = Path(dossier)
    
    # Vérifier que le dossier racine existe bien.
    if not chemin.exists() or not chemin.is_dir():
        print(f"Erreur : Le dossier '{dossier}' n'existe pas.")
        return

    total_tokens = 0
    types_uniques = set()
    
    # Chercher tous les fichiers .txt dans le dossier et ses sous-dossiers.
    fichiers_txt = list(chemin.rglob('*.txt'))
    print(f"Analyse NLP de {len(fichiers_txt)} fichier(s) en cours...\n")

    # ==========================================
    # ANALYSE DES FICHIERS
    # ==========================================
    for index, fichier in enumerate(fichiers_txt, 1):
        # Afficher la progression tous les 50 fichiers.
        if index % 50 == 0:
            print(f"Progression : {index} / {len(fichiers_txt)} fichiers analysés...")
            
        try:
            with open(fichier, 'r', encoding='utf-8') as f:
                contenu = f.read()
                
                # Passer le texte au moteur NLP spaCy. Il va découper intelligemment les mots.
                # Pour éviter de surcharger la RAM sur de très longs fichiers, 
                # augmenter la limite de longueur si nécessaire (ici définie à 2 millions de caractères).
                nlp.max_length = 2000000 
                doc = nlp(contenu)
                
                # Boucler sur chaque token identifié par spaCy.
                for token in doc:
                    # token.is_alpha vérifie que le token est bien composé de lettres.
                    # Cela exclut automatiquement la ponctuation, les chiffres et les espaces.
                    if token.is_alpha:
                        total_tokens += 1
                        # Ajouter le mot en minuscules dans le set pour compter les Types.
                        types_uniques.add(token.text.lower())
                
        except UnicodeDecodeError:
            print(f"Fichier ignoré (problème d'encodage) : {fichier.name}")
        except Exception as e:
            print(f"Erreur lors de la lecture de {fichier.name} : {e}")

    nombre_types = len(types_uniques)
    uber_index = None

    # ==========================================
    # CALCUL DE L'UBER INDEX
    # ==========================================
    # S'assurer qu'il y a des données pour éviter les erreurs mathématiques.
    if total_tokens > 0 and nombre_types > 0:
        log_n = math.log(total_tokens)
        log_v = math.log(nombre_types)
        
        if log_n != log_v:
            uber_index = (log_n ** 2) / (log_n - log_v)
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
            json.dump(resultats, f_json, indent=4, ensure_ascii=False)
    except Exception as e:
         print(f"Erreur lors de la sauvegarde du fichier JSON : {e}")

    # ==========================================
    # AFFICHAGE DES RÉSULTATS
    # ==========================================
    print("\n=== RÉSULTATS DE L'ANALYSE NLP ===")
    print(f"Tokens : {total_tokens:,}".replace(',', ' '))
    print(f"Types  : {nombre_types:,}".replace(',', ' '))
    if uber_index:
        print(f"Uber Index : {uber_index}")
    
    print(f"\nLes résultats ont été sauvegardés dans : {chemin_sortie_json}")

# ==========================================
# CONFIGURATION
# ==========================================
# Remplacer ces chemins par les chemins réels.
dossier_cible = r"D:\myFiles\My Documents\Corpus pour calculs\corpus v5\Trump" 
fichier_json = r"D:\myFiles\My Documents\Corpus pour calculs\resultats_v5_nlp_trump.json"

analyser_corpus_nlp(dossier_cible, fichier_json)