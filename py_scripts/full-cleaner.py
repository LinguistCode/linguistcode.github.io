### ---------------------
# Full cleaning pass on the raw APP (American Presidency Project) files.
# For each .txt in the folder:
#   - rename it "Initial - date - title.txt" (B / O / T, X if unknown),
#   - drop the 5 header lines,
#   - remove the crowd-reaction brackets ([Laughter], [Applause]...),
#   - log every "President (Bush|Obama|Trump):" speaker tag found,
#  - log every OTHER bracket so I can check it by hand.
# Replaces cleaning-corpus.py (same renaming, but targeted cleaning + reports).
### ---------------------

import os
import re
import json
import glob

def corpus_full_cleaner(dossier):
    # Two dicts that end up as the two JSON reports.
    # {speaker expression: [files where it appears]}
    president_marker = {}
    
    # {file: [unexpected bracket contents]}
    odd_brackets = {}

    # Whitelist: brackets deleted silently. Anything else stays in the text
    # and gets reported, because it may be a real editorial note.
    crowd_brackets = {
        "laughter", "applause", "inaudible", "booing", "boos", "mild cheering", 
        "cheers and applause", "cheering", "cheers", "cheer", "laugh", "laughs", 
        "laughters", "laughter", "singing", "shouting", "shouts", "shout", 
        "chanting", "yelling", "chants", "yells"
    }

    # Speaker tags: "(The) President (Bush|Obama|Trump)" followed by "." or ":".
    # IGNORECASE so casing does not matter.
    # (?: ... ) = non-capturing groups; the outer parentheses make findall()
    # return the whole expression.
    regex_president = re.compile(r'(\b(?:The\s+)?President(?:\s+(?:Bush|Obama|Trump))?[\.:])', re.IGNORECASE)
    
    # Only the .txt files directly in the folder (NOT recursive).
    chemin_recherche = os.path.join(dossier, "*.txt")
    fichiers_txt = glob.glob(chemin_recherche)

    # Nothing found -> probably a wrong path.
    if not fichiers_txt:
        print("Aucun discours trouvé dans le dossier. Vérifier le chemin d'accès.")
        return

    for chemin_fichier in fichiers_txt:
        try:
            # readlines() -> I need line numbers for the header fields.
            with open(chemin_fichier, 'r', encoding='utf-8') as f:
                lignes = f.readlines()
        except UnicodeDecodeError:
            print(f"Erreur d'encodage avec le fichier : {chemin_fichier}")
            continue

        # Fewer than 5 lines = no proper APP header -> skip, or lignes[4] crashes.
        if len(lignes) < 5:
            continue

        ### ---------------------
        # NEW FILE NAME
        ### ---------------------
        # Line 1 holds the president's name -> initial for the file name.
        premiere_ligne = lignes[0].lower()
        
        if "bush" in premiere_ligne:
            initiale = "B"
        elif "obama" in premiere_ligne:
            initiale = "O"
        elif "trump" in premiere_ligne:
            initiale = "T"
        else:
            # X = none of the three -> check these files by hand.
            initiale = "X"

        # Line 3 = date.
        date_fichier = lignes[2].strip()
        
        # Line 5 = title, cut to 30 characters to keep names short.
        titre_fichier = lignes[4].strip()[:30]

        # Characters Windows refuses in file names: "-" in the date, removed in the title.
        date_propre = re.sub(r'[\\/*?:"<>|]', '-', date_fichier)
        titre_propre = re.sub(r'[\\/*?:"<>|]', '', titre_fichier)

        nouveau_nom = f"{initiale} - {date_propre} - {titre_propre}.txt"
        nouveau_chemin = os.path.join(dossier, nouveau_nom)

        # Body of the speech = everything after the 5 header lines.
        contenu_restant = "".join(lignes[5:])

        ### ---------------------
        # REPORT 1: speaker tags
        ### ---------------------
        expressions_trouvees = regex_president.findall(contenu_restant)
        
        for expr in expressions_trouvees:
            # Create the key the first time this exact expression shows up.
            if expr not in president_marker:
                president_marker[expr] = []
            # One entry per file, even if the tag appears 50 times in it.
            if nouveau_nom not in president_marker[expr]:
                president_marker[expr].append(nouveau_nom)

        ### ---------------------
        # REPORT 2: unexpected brackets
        ### ---------------------
        tous_les_crochets = re.findall(r'\[(.*?)\]', contenu_restant)
        
        # Everything that is not in the whitelist.
        crochets_inattendus = [c for c in tous_les_crochets if c.strip().lower() not in crowd_brackets]
        
        # Only files with at least one unexpected bracket go into the report.
        if crochets_inattendus:
            odd_brackets[nouveau_nom] = crochets_inattendus

        ### ---------------------
        # TARGETED CLEANING
        ### ---------------------
        # One regex built from the whitelist; \s* also catches "[ Laughter ]".
        regex_delete_brackets = r'\[\s*(' + '|'.join(crowd_brackets) + r')\s*\]'
        
        # Case-insensitive removal of the whitelisted brackets only:
        # the unexpected ones do not match and stay in the text.
        contenu_nettoye = re.sub(regex_delete_brackets, '', contenu_restant, flags=re.IGNORECASE)

        with open(nouveau_chemin, 'w', encoding='utf-8') as f:
            f.write(contenu_nettoye)

        # Delete the original so only the renamed, cleaned file is left.
        # (If two speeches end up with the same name, the second overwrites the first!)
        if chemin_fichier != nouveau_chemin:
            os.remove(chemin_fichier)
            
        print(f"Success : {nouveau_nom} created")

    ### ---------------------
    # JSON REPORTS
    ### ---------------------
    
    # Both reports are written inside the corpus folder itself.
    chemin_json_president = os.path.join(dossier, "dict_president.json")
    chemin_json_crochets = os.path.join(dossier, "dict_other_brackets.json")

    with open(chemin_json_president, 'w', encoding='utf-8') as f:
        json.dump(president_marker, f, indent=4, ensure_ascii=False)
        
    with open(chemin_json_crochets, 'w', encoding='utf-8') as f:
        json.dump(odd_brackets, f, indent=4, ensure_ascii=False)

    print("\nOpération terminée.")
    print(f"Rapport Président généré : {chemin_json_president}")
    print(f"Rapport Crochets généré : {chemin_json_crochets}")

### ---------------------
# PATH
### ---------------------
# WARNING: renames and DELETES the original files -> run it on a copy.
chemin_du_dossier = r"D:\Local_corpus" 

corpus_full_cleaner(chemin_du_dossier)
