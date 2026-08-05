# ==========================================
# Cleaning and renaming APP files
# ==========================================

import os
import re
import glob

def traiter_fichiers_txt(dossier):
    # Cherche tous les fichiers .txt dans le dossier spécifié
    chemin_recherche = os.path.join(dossier, "*.txt")
    fichiers_txt = glob.glob(chemin_recherche)

    if not fichiers_txt:
        print("Aucun fichier .txt trouvé dans le dossier.")
        return

    for chemin_fichier in fichiers_txt: # Lire le contenu du fichier
        try:
            with open(chemin_fichier, 'r', encoding='utf-8') as f:
                lignes = f.readlines()
        except UnicodeDecodeError:
            print(f"Erreur d'encodage avec le fichier (essayez 'latin-1' si besoin) : {chemin_fichier}")
            continue

        # Vérifier que le fichier a au moins 5 lignes
        if len(lignes) < 5:
            print(f"Ignoré (moins de 5 lignes) : {os.path.basename(chemin_fichier)}")
            continue

        # 1. Récupérer la 3ème ligne (index 2) pour la date
        date_fichier = lignes[2].strip()
        
        # 2. Récupérer les 30 premiers caractères de la 5ème ligne (index 4) pour le titre
        titre_fichier = lignes[4].strip()[:30]

        # Nettoyer la date et le titre pour éviter les caractères interdits dans les noms de fichiers (\, /, :, *, ?, ", <, >, |)
        date_propre = re.sub(r'[\\/*?:"<>|]', '-', date_fichier)
        titre_propre = re.sub(r'[\\/*?:"<>|]', '', titre_fichier)

        # Créer le nouveau nom de fichier
        nouveau_nom = f"B - {date_propre} - {titre_propre}.txt"
        nouveau_chemin = os.path.join(dossier, nouveau_nom)

        # 3. Supprimer les 5 premières lignes
        contenu_restant = "".join(lignes[5:])

        # 4. Supprimer toutes les expressions entre crochets (ex: [texte])
        # r'\[.*?\]' cherche un crochet ouvrant, n'importe quel texte (le moins possible), puis un crochet fermant.
        contenu_nettoye = re.sub(r'\[.*?\]', '', contenu_restant)

        # Sauvegarder le nouveau contenu dans le nouveau fichier
        with open(nouveau_chemin, 'w', encoding='utf-8') as f:
            f.write(contenu_nettoye)

        # Supprimer l'ancien fichier s'il a changé de nom
        if chemin_fichier != nouveau_chemin:
            os.remove(chemin_fichier)
            
        print(f"Succès : {os.path.basename(chemin_fichier)} -> {nouveau_nom}")

# ==========================================
# UTILISATION
# ==========================================

chemin_du_dossier = r"G:\My Drive\00 - Université\00 - Doctorat\00 - Recherches These\00 - Corpus\BUSH - Janvier à mars 2004 v1" 

traiter_fichiers_txt(chemin_du_dossier)