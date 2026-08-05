import os
import re
import json
import glob

def corpus_full_cleaner(dossier):
    # Il faut commencer par préparer les dictionnaires pour les fichiers JSON.
    # Créer un dictionnaire pour classer les fichiers selon les expressions du Président.
    president_marker = {}
    
    # Préparer un dictionnaire pour lister les crochets par fichier.
    odd_brackets = {}

    # Définir la liste exacte des mots entre crochets autorisés à être supprimés sans alerte.
    crowd_brackets = {
        "laughter", "applause", "inaudible", "booing", "boos", "mild cheering", 
        "cheers and applause", "cheering", "cheers", "cheer", "laugh", "laughs", 
        "laughters", "laughter", "singing", "shouting", "shouts", "shout", 
        "chanting", "yelling", "chants", "yells"
    }

    # Preparer le regex pour trouver "(The) President (Bush|Obama|Trump)(.|:)"
    # re.IGNORECASE pour ne pas prendre la casse en comtpe.
    # (?: ... ) crée un groupe non capturant, et les parenthèses garantissent que .findall() renvoie l'expression entièree.
    regex_president = re.compile(r'(\b(?:The\s+)?President(?:\s+(?:Bush|Obama|Trump))?[\.:])', re.IGNORECASE)
    
    # Aller chercher tous les fichiers textes présents dans le dossier cible.
    chemin_recherche = os.path.join(dossier, "*.txt")
    fichiers_txt = glob.glob(chemin_recherche)

    # S'assurer qu'il y a bien des fichiers à traiter avant de continuer.
    if not fichiers_txt:
        print("Aucun discours trouvé dans le dossier. Vérifier le chemin d'accès.")
        return

    # Il faut maintenant boucler sur chaque fichier trouvé.
    for chemin_fichier in fichiers_txt:
        try:
            # Ouvrir le fichier en lecture et récupérer toutes les lignes.
            with open(chemin_fichier, 'r', encoding='utf-8') as f:
                lignes = f.readlines()
        except UnicodeDecodeError:
            print(f"Erreur d'encodage avec le fichier : {chemin_fichier}")
            continue

        # Faire bien attention à ignorer les fichiers trop courts pour pas faire planter le script.
        if len(lignes) < 5:
            continue

        # Isoler la première ligne et la passer en minuscules pour ignorer la casse.
        premiere_ligne = lignes[0].lower()
        
        # Chercher précisément les noms cibles et attribuer la bonne initiale.
        if "bush" in premiere_ligne:
            initiale = "B"
        elif "obama" in premiere_ligne:
            initiale = "O"
        elif "trump" in premiere_ligne:
            initiale = "T"
        else:
            # Mettre un X par défaut si aucun des trois noms n'est reconnu.
            initiale = "X"

        # Aller récupérer la date sur la troisième ligne.
        date_fichier = lignes[2].strip()
        
        # Isoler les 30 premiers caractères de la cinquième ligne pour le titre.
        titre_fichier = lignes[4].strip()[:30]

        # Penser à nettoyer les variables pour ne pas avoir de caractères interdits dans le nom de fichier.
        date_propre = re.sub(r'[\\/*?:"<>|]', '-', date_fichier)
        titre_propre = re.sub(r'[\\/*?:"<>|]', '', titre_fichier)

        # Construire le nouveau nom de fichier avec le format demandé.
        nouveau_nom = f"{initiale} - {date_propre} - {titre_propre}.txt"
        nouveau_chemin = os.path.join(dossier, nouveau_nom)

        # Joindre le reste du texte en supprimant les 5 premières lignes.
        contenu_restant = "".join(lignes[5:])

        # Étape d'analyse : chercher toutes les occurrences liées au Président dans le texte restant.
        expressions_trouvees = regex_president.findall(contenu_restant)
        
        # S'il y a des expressions, il faut les classer dans le dictionnaire pour le JSON.
        for expr in expressions_trouvees:
            # S'assurer que l'expression existe comme clé, sinon la créer.
            if expr not in president_marker:
                president_marker[expr] = []
            # Ajouter le nouveau nom du fichier à la liste de cette expression s'il n'y est pas déjà.
            if nouveau_nom not in president_marker[expr]:
                president_marker[expr].append(nouveau_nom)

        # Étape d'analyse des crochets : lister tous les textes présents entre crochets.
        tous_les_crochets = re.findall(r'\[(.*?)\]', contenu_restant)
        
        # Vérifier s'il y a au moins un crochet qui ne figure pas dans la liste des mots autorisés.
        crochets_inattendus = [c for c in tous_les_crochets if c.strip().lower() not in crowd_brackets]
        
        # NOUVEAU : S'il y a des crochets inattendus, associer la liste de ces crochets au nom du fichier.
        if crochets_inattendus:
            odd_brackets[nouveau_nom] = crochets_inattendus

        # Construire une expression régulière avec la liste des mots à supprimer (\s* permet de gérer les espaces éventuels comme [ Laughter ] )
        regex_delete_brackets = r'\[\s*(' + '|'.join(crowd_brackets) + r')\s*\]'
        
        # Procéder au nettoyage ciblé : supprimer uniquement ces expressions en ignorant la casse
        # Les crochets "inattendus" ne correspondant pas à la regex resteront intacts.
        contenu_nettoye = re.sub(regex_delete_brackets, '', contenu_restant, flags=re.IGNORECASE)

        # Créer et écrire le nouveau fichier propre avec le bon contenu.
        with open(nouveau_chemin, 'w', encoding='utf-8') as f:
            f.write(contenu_nettoye)

        # Détruire l'ancien fichier pour ne conserver que le nouveau.
        if chemin_fichier != nouveau_chemin:
            os.remove(chemin_fichier)
            
        print(f"Success : {nouveau_nom} created")

    # ==========================================
    # GÉNÉRATION DES FICHIERS JSON
    # ==========================================
    
    # Définir les chemins pour sauvegarder les deux rapports JSON.
    chemin_json_president = os.path.join(dossier, "dict_president.json")
    chemin_json_crochets = os.path.join(dossier, "dict_other_brackets.json")

    # Ouvrir et sauvegarder le dictionnaire des expressions du Président en JSON.
    with open(chemin_json_president, 'w', encoding='utf-8') as f:
        json.dump(president_marker, f, indent=4, ensure_ascii=False)
        
    # Ouvrir et sauvegarder le dictionnaire des fichiers et de leurs crochets inattendus.
    with open(chemin_json_crochets, 'w', encoding='utf-8') as f:
        json.dump(odd_brackets, f, indent=4, ensure_ascii=False)

    print("\nOpération terminée.")
    print(f"Rapport Président généré : {chemin_json_president}")
    print(f"Rapport Crochets généré : {chemin_json_crochets}")

# ==========================================
# Chemin
# ==========================================
chemin_du_dossier = r"D:\Local_corpus" 

corpus_full_cleaner(chemin_du_dossier)