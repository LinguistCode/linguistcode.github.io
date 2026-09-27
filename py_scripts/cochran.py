### ---------------------
# Cochran's formula: how many concordance lines do I need to annotate by hand
# for the sample to be representative? Includes the finite-population correction.
### ---------------------

import math


def calculer_echantillon_cochran():
    print("=== CALCULATEUR METHODOLOGIQUE : FORMULE DE COCHRAN ===")
    print("Ajustement de l'échantillon pour une population finie\n")

    ### ---------------------
    # 1. PARAMETERS (Enter = thesis default value)
    ### ---------------------
    try:
        # N = total number of lines in the population (whole concordance).
        N_input = input("-> Taille totale de la population (N) [Défaut: 9958] : ")
        N = int(N_input) if N_input.strip() else 9958

        # Z = z-score for the confidence level (1.96 -> 95%).
        Z_input = input("-> Valeur de l'écart-réduit (Z) [Défaut: 1.96 pour 95%] : ")
        Z = float(Z_input) if Z_input.strip() else 1.96

        # p = expected proportion. 0.5 = maximum variance = safest (largest) sample.
        p_input = input(
            "-> Proportion présumée (p) [Défaut: 0.5 pour variance max] : "
            )
        p = float(p_input) if p_input.strip() else 0.5
        q = 1 - p

        # e = accepted margin of error (0.05 -> +/- 5%).
        e_input = input("-> Marge d'erreur tolérée (e) [Défaut: 0.05 pour 5%] : ")
        e = float(e_input) if e_input.strip() else 0.05

    except ValueError:
        print("\n[Erreur] Veuillez entrer des valeurs numériques valides.")
        return

    ### ---------------------
    # 2. SAMPLE FOR AN INFINITE POPULATION
    # n0 = (Z^2 * p * q) / e^2
    ### ---------------------
    n0 = (pow(Z, 2) * p * q) / pow(e, 2)

    ### ---------------------
    # 3. FINITE-POPULATION CORRECTION
    # n = n0 / (1 + (n0 - 1) / N) -> smaller than n0 because N is known and limited.
    ### ---------------------
    n_final = n0 / (1 + ((n0 - 1) / N))

    ### ---------------------
    # 4. RESULTS (always round UP, never down)
    ### ---------------------
    print("\n" + "-" * 50)
    print("RÉSULTATS DE L'ANALYSE STATISTIQUE :")
    print("-" * 50)
    print(f"• Variance maximale estimée (p*q) : {p * q}")
    print(f"• Échantillon théorique brut (n₀) : {n0:.4f} lignes")
    print(f"• Échantillon minimal requis réajusté (n) : {n_final:.2f} lignes")
    print(f"• Taille à retenir (arrondi supérieur)   : {math.ceil(n_final)} lignes")
    print("-" * 50)


# Run only when launched directly (not when imported).
if __name__ == "__main__":
    calculer_echantillon_cochran()