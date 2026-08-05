import json
import pandas as pd

# ==========================================
# 1. CONFIGURATION DES FICHIERS
# ==========================================
# Remplacez par les noms exacts des fichiers Excel
file_p1 = r"D:\myFiles\My Documents\Corpus pour calculs\KEYWORD - BUSH - 100.xlsx"
file_p2 = r"D:\myFiles\My Documents\Corpus pour calculs\KEYWORD - OBAMA - 100.xlsx"
file_p3 = r"D:\myFiles\My Documents\Corpus pour calculs\KEYWORD - TRUMP - 100.xlsx"

# Nom de la colonne Excel qui contient les mots-clés 
colonne_mots = "Item" 

def charger_keywords_excel(chemin_fichier):
    try:
        # Utilisation de read_excel à la place de read_csv
        df = pd.read_excel(chemin_fichier)
        
        # Nettoyage classique : suppression des lignes vides, des espaces et passage en minuscules
        return set(df[colonne_mots].dropna().astype(str).str.strip().str.lower())
            
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier Excel {chemin_fichier} : {e}")
        print(f"Vérifiez que la colonne nommée '{colonne_mots}' existe bien dans ce fichier.")
        return set()

# ==========================================
# 2. CHARGEMENT ET TRAITEMENT DES DONNÉES
# ==========================================
keywords_p1 = charger_keywords_excel(file_p1)
keywords_p2 = charger_keywords_excel(file_p2)
keywords_p3 = charger_keywords_excel(file_p3)

# Vérification méthodologique du volume de données chargées
print(f"Mots chargés : Président 1 ({len(keywords_p1)}), Président 2 ({len(keywords_p2)}), Président 3 ({len(keywords_p3)})")

# Logique des ensembles (Venn)
communs_tous = list(keywords_p1 & keywords_p2 & keywords_p3)

specifiques_p1 = list(keywords_p1 - (keywords_p2 | keywords_p3))
specifiques_p2 = list(keywords_p2 - (keywords_p1 | keywords_p3))
specifiques_p3 = list(keywords_p3 - (keywords_p1 | keywords_p2))

partages_p1_p2 = list((keywords_p1 & keywords_p2) - keywords_p3)
partages_p2_p3 = list((keywords_p2 & keywords_p3) - keywords_p1)
partages_p1_p3 = list((keywords_p1 & keywords_p3) - keywords_p2)

# ==========================================
# 3. STRUCTURATION ET EXPORT JSON
# ==========================================
resultats = {
    "metadonnees": {
        "description": "Comparaison automatique des top 100 keywords à partir de fichiers XLSX",
        "total_distinct_p1": len(keywords_p1),
        "total_distinct_p2": len(keywords_p2),
        "total_distinct_p3": len(keywords_p3)
    },
    "communs_aux_trois": sorted(communs_tous),
    "specifiques_president_1": sorted(specifiques_p1),
    "specifiques_president_2": sorted(specifiques_p2),
    "specifiques_president_3": sorted(specifiques_p3),
    "partages_exclusifs_p1_p2": sorted(partages_p1_p2),
    "partages_exclusifs_p2_p3": sorted(partages_p2_p3),
    "partages_exclusifs_p1_p3": sorted(partages_p1_p3)
}

output_file = "comparaison_keywords_presidents.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(resultats, f, ensure_ascii=False, indent=4)

print(f"\nAnalyse terminée ! Le fichier JSON a été généré sous le nom : '{output_file}'")