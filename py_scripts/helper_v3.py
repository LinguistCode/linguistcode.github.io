### ---------------------
# Small interactive calculator for the stats I keep redoing by hand:
#   1. relative frequency, 2. Uber index, 3. log-likelihood (G2) + p-value.
# v3 = v2 + the enTenTen reference corpus (option 5).
### ---------------------

import math
from scipy.stats import chi2

def main():
    # Corpus sizes in tokens (hard-coded, taken from Sketch Engine).
    # Update these if the corpus is rebuilt!
    corpora = {
        "1": {"name": "Bush Corpus", "tokens": 3439334},
        "2": {"name": "Obama Corpus", "tokens": 3471270},
        "3": {"name": "Trump Corpus", "tokens": 1626297},
        "4": {"name": "Full Corpus", "tokens": 8536901},
        "5": {"name": "enTenTen Corpus", "tokens": 61585997113}
    }

    while True:
        # Main menu, loops until option 4.
        print("\n------- Menu -------")
        print("1. Fréquence relative")
        print("2. Index Über")
        print("3. Log-vraisemblance et p-value")
        print("4. Quitter")
        
        choix = input("\nChoisissez une fonctionnalité (1-4) : ")
        
        if choix == "1":
            ### ---------------------
            # 1. RELATIVE FREQUENCY
            # One corpus + a normalisation base + one or several raw counts.
            ### ---------------------
            print("\n[Fréquence relative]")
            for k, v in corpora.items(): 
                print(f"{k}. {v['name']}")
            
            c = input("Sélectionnez le corpus (1/2/3/4/5) : ")
            scale = int(input("Base de référence (ex: 10000, 100000) : "))
            raw_input = input("Occurrences brutes (séparées par des points-virgules) : ")
            
            n = corpora[c]["tokens"]
            
            # Several counts in one go, separated by ";" (e.g. fear; terror; afraid).
            raw_values = [int(val.strip()) for val in raw_input.split(";")]
            
            # rf = raw / corpus size * base, printed as "(raw) --> rf".
            results = []
            for raw in raw_values:
                rf = (raw / n) * scale
                results.append(f"({raw}) --> {rf:.2f}")
                
            print(f"-> Fréquence relative : {'; '.join(results)}")
            
        elif choix == "2":
            ### ---------------------
            # 2. UBER INDEX
            # Tokens and types typed in directly
            ### ---------------------
            print("\n[Index Über]")
            tokens = int(input("Nombre total de tokens : "))
            types = int(input("Nombre de types uniques : "))
            
            # Guard: log(1) = 0 and tokens == types -> division by zero.
            if tokens > 1 and types > 1 and tokens != types:
                u = (math.log(tokens) ** 2) / (math.log(tokens) - math.log(types))
                print(f"-> Index Über : {u:.2f}")
            else:
                print("-> Erreur : Les tokens et types doivent être supérieurs à 1 et différents.")
                
        elif choix == "3":
            ### ---------------------
            # 3. LOG-LIKELIHOOD (G2) + P-VALUE
            # Two DIFFERENT corpora + the raw count of the word in each.
            ### ---------------------
            print("\n[Log-vraisemblance et p-value]")
            for k, v in corpora.items(): 
                print(f"{k}. {v['name']}")
                
            c1 = input("Corpus 1 (1/2/3/4/5) : ")
            c2 = input("Corpus 2 (1/2/3/4/5) : ")
            o1 = int(input(f"Occurrences brutes dans {corpora[c1]['name']} : "))
            o2 = int(input(f"Occurrences brutes dans {corpora[c2]['name']} : "))
            
            n1, n2 = corpora[c1]["tokens"], corpora[c2]["tokens"]

            ### ---------------------
            # Full 2x2 contingency table (standard method, Dunning 1993):
            #              word       rest of corpus
            # Corpus 1     o1         n1 - o1
            # Corpus 2     o2         n2 - o2
            ### ---------------------
            autre1 = n1 - o1
            autre2 = n2 - o2

            total_mot = o1 + o2
            total_autre = autre1 + autre2
            total_n = n1 + n2

            # Expected counts = row total * column total / grand total.
            e1 = n1 * total_mot / total_n
            e2 = n2 * total_mot / total_n
            e_autre1 = n1 * total_autre / total_n
            e_autre2 = n2 * total_autre / total_n

            # G2 = 2 * sum(O * ln(O/E)); zero cells skipped (0 * ln 0 -> 0).
            g2 = 0.0
            for o, e in [(o1, e1), (o2, e2), (autre1, e_autre1), (autre2, e_autre2)]:
                if o > 0 and e > 0:
                    g2 += o * math.log(o / e)
            g2 *= 2

            # G2 follows a chi2 with 1 df -> p-value = survival function.
            p_val = chi2.sf(g2, 1)
            print(f"-> Log-Likelihood (G2) : {g2:.4f}")
            print(f"-> p-value : {p_val:.4e}")
            
            if p_val < 0.05:
                print("-> Résultat : La différence est statistiquement significative (p < 0.05).")
            else:
                print("-> Résultat : La différence n'est pas statistiquement significative (p >= 0.05).")
            
        elif choix == "4":
            print("Fermeture du programme.")
            break
        
        else:
            print("Choix invalide, veuillez réessayer.")

if __name__ == "__main__":
    main()