import math


def calculer_echantillon_cochran():
    print("=== CALCULATEUR METHODOLOGIQUE : FORMULE DE COCHRAN ===")
    print("Ajustement de l'échantillon pour une population finie\n")

    # 1. Collecte des paramètres avec valeurs par défaut de la thèse
    try:
        # Taille totale du corpus (N)
        N_input = input("-> Taille totale de la population (N) [Défaut: 9958] : ")
        N = int(N_input) if N_input.strip() else 9958

        # Score Z (Z-score lié au niveau de confiance)
        Z_input = input("-> Valeur de l'écart-réduit (Z) [Défaut: 1.96 pour 95%] : ")
        Z = float(Z_input) if Z_input.strip() else 1.96

        # Proportion présumée (p)
        p_input = input(
            "-> Proportion présumée (p) [Défaut: 0.5 pour variance max] : "
            )
        p = float(p_input) if p_input.strip() else 0.5
        q = 1 - p

        # Marge d'erreur tolérée (e)
        e_input = input("-> Marge d'erreur tolérée (e) [Défaut: 0.05 pour 5%] : ")
        e = float(e_input) if e_input.strip() else 0.05

    except ValueError:
        print("\n[Erreur] Veuillez entrer des valeurs numériques valides.")
        return

    # 2. Calcul de l'échantillon théorique pour population infinie (n0)
    # Formule : n0 = (Z^2 * p * q) / e^2
    n0 = (pow(Z, 2) * p * q) / pow(e, 2)

    # 3. Calcul de l'échantillon corrigé pour population finie (n)
    # Formule : n = n0 / (1 + (n0 - 1) / N)
    n_final = n0 / (1 + ((n0 - 1) / N))

    # 4. Affichage des résultats
    print("\n" + "-" * 50)
    print("RÉSULTATS DE L'ANALYSE STATISTIQUE :")
    print("-" * 50)
    print(f"• Variance maximale estimée (p*q) : {p * q}")
    print(f"• Échantillon théorique brut (n₀) : {n0:.4f} lignes")
    print(f"• Échantillon minimal requis réajusté (n) : {n_final:.2f} lignes")
    print(f"• Taille à retenir (arrondi supérieur)   : {math.ceil(n_final)} lignes")
    print("-" * 50)


# Exécution du script
if __name__ == "__main__":
    calculer_echantillon_cochran()