### ---------------------
# Compare the top-100 keyword lists of the three presidents (Sketch Engine
# keyword exports, .xlsx) with plain set logic: shared by all three,
# specific to one, shared by exactly two. Output = one JSON file.
### ---------------------

import json
import pandas as pd

### ---------------------
# 1. INPUT FILES
### ---------------------
# P1 / P2 / P3 = Bush / Obama / Trump. Keep that order, the JSON keys only say p1/p2/p3.
file_p1 = r"D:\myFiles\My Documents\Corpus pour calculs\KEYWORD - BUSH - 100.xlsx"
file_p2 = r"D:\myFiles\My Documents\Corpus pour calculs\KEYWORD - OBAMA - 100.xlsx"
file_p3 = r"D:\myFiles\My Documents\Corpus pour calculs\KEYWORD - TRUMP - 100.xlsx"

# Name of the column holding the keywords in the Sketch Engine export.
colonne_mots = "Item" 

def charger_keywords_excel(chemin_fichier):
    try:
        df = pd.read_excel(chemin_fichier)
        
        ### Drop empty cells, trim spaces, lowercase -> returned as a set.
        return set(df[colonne_mots].dropna().astype(str).str.strip().str.lower())
            
    except Exception as e:
        ### Most common cause: the column is not called "Item" in that export.
        print(f"Erreur lors de la lecture du fichier Excel {chemin_fichier} : {e}")
        print(f"Vérifiez que la colonne nommée '{colonne_mots}' existe bien dans ce fichier.")
        return set()

### ---------------------
# 2. LOAD + SET LOGIC
### ---------------------
keywords_p1 = charger_keywords_excel(file_p1)
keywords_p2 = charger_keywords_excel(file_p2)
keywords_p3 = charger_keywords_excel(file_p3)

# Check: should print ~100 per president. Fewer = duplicates after lowercasing, or a loading problem.
print(f"Mots chargés : Président 1 ({len(keywords_p1)}), Président 2 ({len(keywords_p2)}), Président 3 ({len(keywords_p3)})")

# Venn diagram zones: & = intersection, | = union, - = difference.
communs_tous = list(keywords_p1 & keywords_p2 & keywords_p3)

specifiques_p1 = list(keywords_p1 - (keywords_p2 | keywords_p3))
specifiques_p2 = list(keywords_p2 - (keywords_p1 | keywords_p3))
specifiques_p3 = list(keywords_p3 - (keywords_p1 | keywords_p2))

# Shared by exactly two presidents (the third one removed).
partages_p1_p2 = list((keywords_p1 & keywords_p2) - keywords_p3)
partages_p2_p3 = list((keywords_p2 & keywords_p3) - keywords_p1)
partages_p1_p3 = list((keywords_p1 & keywords_p3) - keywords_p2)

### ---------------------
# 3. JSON EXPORT
### ---------------------
# Lists sorted alphabetically so two runs give the exact same file.
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