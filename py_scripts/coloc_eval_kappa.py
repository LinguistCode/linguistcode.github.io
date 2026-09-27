### ---------------------
# Step 2 after coloc_eval.py: how reliable is the automatic valence?
# Compares the script's "Valence" column with my manual "Verification"
# column -> raw agreement, Cohen's kappa, confusion matrix, list of disagreements.
### ---------------------

import sys
import re
import openpyxl
from collections import Counter


def extraire_label(valeur):
    ### ---------------------
    # Get the bare label (Positif / Négatif / Neutre / Non trouvé) out of a cell.
    # The cell is either already a label, or the full script output like "Positif (+0.620, VADER)".
    ### ---------------------
    if valeur is None:
        return None
    texte = str(valeur).strip()
    if not texte:
        return None
    # Label = first word, or first two words ("Non trouvé"), before any parenthesis.
    match = re.match(r"^([A-Za-zÀ-ÿ]+(?:\s[A-Za-zÀ-ÿ]+)?)", texte)
    if not match:
        return texte
    return match.group(1).strip()


def trouver_colonne(ws, nom_recherche):
    ### ---------------------
    # Column number whose header (row 1) contains the name I'm looking for.
    # Case-insensitive substring match, so "Valence (auto)" is found too.
    ### ---------------------
    for col in range(1, ws.max_column + 1):
        entete = ws.cell(row=1, column=col).value
        if entete and nom_recherche.lower() in str(entete).lower():
            return col
    return None


def kappa_cohen(paires):
    ### ---------------------
    # Cohen's kappa from a list of (auto_label, manual_label) pairs.
    # kappa = (observed agreement - expected agreement) / (1 - expected agreement)
    # Expected agreement = what two raters would reach by chance, given how often each of them uses each label.
    ### ---------------------
    n = len(paires)
    if n == 0:
        return None

    accord_observe = sum(1 for a, m in paires if a == m) / n

    labels = sorted(set([a for a, m in paires] + [m for a, m in paires]))
    compte_auto = Counter(a for a, m in paires)
    compte_manuel = Counter(m for a, m in paires)

    accord_attendu = sum(
        (compte_auto[l] / n) * (compte_manuel[l] / n) for l in labels
    )

    if accord_attendu == 1:
        return 1.0  # edge case: a single label everywhere -> formula would divide by 0

    kappa = (accord_observe - accord_attendu) / (1 - accord_attendu)
    return kappa


def interpretation_kappa(k):
    # Landis & Koch (1977) scale, the one everybody quotes in linguistics.
    if k < 0:
        return "désaccord (pire qu'un accord aléatoire)"
    if k < 0.20:
        return "accord très faible"
    if k < 0.40:
        return "accord faible"
    if k < 0.60:
        return "accord modéré"
    if k < 0.80:
        return "accord substantiel"
    return "accord quasi parfait"


def main(fichier):
    # data_only=True -> read the cached cell values, not the formulas.
    wb = openpyxl.load_workbook(fichier, data_only=True)
    ws = wb.active

    col_valence = trouver_colonne(ws, "Valence")
    col_verif = trouver_colonne(ws, "Verification")
    # also accept the accented spelling "Vérification"
    if col_verif is None:
        col_verif = trouver_colonne(ws, "Vérification")

    if col_valence is None or col_verif is None:
        print("Erreur : impossible de trouver les colonnes 'Valence' et/ou "
              "'Verification' (vérifie l'en-tête en ligne 1).")
        sys.exit(1)

    paires = []
    lignes_ignorees = 0

    for row in range(2, ws.max_row + 1):
        auto = extraire_label(ws.cell(row=row, column=col_valence).value)
        manuel = extraire_label(ws.cell(row=row, column=col_verif).value)

        if auto is None or manuel is None:
            continue  # row not checked by hand yet -> skip it
        if auto == "Non trouvé":
            # The script could not score this one: 
            # count it apart instead of letting it distort the agreement figures.
            lignes_ignorees += 1
            continue

        paires.append((auto, manuel))

    if not paires:
        print("Aucune paire (Valence, Verification) exploitable trouvée.")
        sys.exit(1)

    n = len(paires)
    accords = [(a, m) for a, m in paires if a == m]
    desaccords = [(a, m) for a, m in paires if a != m]
    taux_accord = len(accords) / n * 100
    kappa = kappa_cohen(paires)

    # Confusion matrix: rows = manual (reference), columns = script.
    labels = sorted(set([a for a, m in paires] + [m for a, m in paires]))
    matrice = {l: Counter() for l in labels}
    for a, m in paires:
        matrice[m][a] += 1

    ### ---------------------
    ### DISPLAY
    ### ---------------------
    print(f"Fichier : {fichier}")
    print(f"Lignes comparées : {n} "
          f"(+ {lignes_ignorees} ignorées car 'Non trouvé' par le script)")
    print()
    print(f"Taux d'accord simple : {taux_accord:.1f} %  "
          f"({len(accords)}/{n})")
    print(f"Kappa de Cohen        : {kappa:.3f}  "
          f"({interpretation_kappa(kappa)})")
    print()

    print("Matrice de confusion (lignes = annotation manuelle, "
          "colonnes = script) :")
    entete = "".ljust(14) + "".join(l.ljust(12) for l in labels)
    print(entete)
    for l_manuel in labels:
        ligne = l_manuel.ljust(14)
        for l_auto in labels:
            ligne += str(matrice[l_manuel][l_auto]).ljust(12)
        print(ligne)
    print()

    # Most frequent disagreement types first -> says where the script goes wrong.
    if desaccords:
        print(f"Détail des {len(desaccords)} désaccords (script -> manuel) :")
        compte_desaccords = Counter(desaccords)
        for (a, m), c in compte_desaccords.most_common():
            print(f"  {a} -> {m} : {c} cas")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage : python comparer_annotations.py fichier.xlsx")
        sys.exit(1)
    main(sys.argv[1])
