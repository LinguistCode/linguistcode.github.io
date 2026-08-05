import math
from scipy.stats import chi2

def main():
    # Définition des corpus et de leurs tailles respectives
    corpora = {
        "1": {"name": "Bush Corpus", "tokens": 3439334},
        "2": {"name": "Obama Corpus", "tokens": 3471270},
        "3": {"name": "Trump Corpus", "tokens": 1626297},
        "4": {"name": "Full Corpus", "tokens": 8536901}
    }

    while True:
        # Choix de la fonctionnalité
        print("\n------- Menu -------")
        print("1. Fréquence relative")
        print("2. Index Über")
        print("3. Log-vraisemblance et p-value")
        print("4. Quitter")
        
        choix = input("\nChoisissez une fonctionnalité (1-4) : ")
        
        if choix == "1":
            # Requiert la sélection d'un seul corpus, la base de référence et les occurrences brutes
            print("\n[Fréquence relative]")
            for k, v in corpora.items(): 
                print(f"{k}. {v['name']}")
            
            c = input("Sélectionnez le corpus (1/2/3/4) : ")
            scale = int(input("Base de référence (ex: 10000, 100000) : "))
            raw_input = input("Occurrences brutes (séparées par des points-virgules) : ")
            
            n = corpora[c]["tokens"]
            
            # Extract and clean up multiple values separated by ';'
            raw_values = [int(val.strip()) for val in raw_input.split(";")]
            
            # Calculate relative frequency for each value and format the output
            results = []
            for raw in raw_values:
                rf = (raw / n) * scale
                results.append(f"({raw}) --> {rf:.2f}")
                
            print(f"-> Fréquence relative : {'; '.join(results)}")
            
        elif choix == "2":
            # Saisie directe des tokens totaux et types uniques
            print("\n[Index Über]")
            tokens = int(input("Nombre total de tokens : "))
            types = int(input("Nombre de types uniques : "))
            
            if tokens > 1 and types > 1 and tokens != types:
                u = (math.log(tokens) ** 2) / (math.log(tokens) - math.log(types))
                print(f"-> Index Über : {u:.2f}")
            else:
                print("-> Erreur : Les tokens et types doivent être supérieurs à 1 et différents.")
                
        elif choix == "3":
            # Requiert la sélection de deux corpus distincts pour comparaison
            print("\n[Log-vraisemblance et p-value]")
            for k, v in corpora.items(): 
                print(f"{k}. {v['name']}")
                
            c1 = input("Corpus 1 (1/2/3/4) : ")
            c2 = input("Corpus 2 (1/2/3/4) : ")
            o1 = int(input(f"Occurrences brutes dans {corpora[c1]['name']} : "))
            o2 = int(input(f"Occurrences brutes dans {corpora[c2]['name']} : "))
            
            n1, n2 = corpora[c1]["tokens"], corpora[c2]["tokens"]

            # Tableau de contingence 2x2 complet (méthode standard, Dunning 1993) :
            #              mot        reste du corpus
            # Corpus 1     o1         n1 - o1
            # Corpus 2     o2         n2 - o2
            autre1 = n1 - o1
            autre2 = n2 - o2

            total_mot = o1 + o2
            total_autre = autre1 + autre2
            total_n = n1 + n2

            e1 = n1 * total_mot / total_n
            e2 = n2 * total_mot / total_n
            e_autre1 = n1 * total_autre / total_n
            e_autre2 = n2 * total_autre / total_n

            g2 = 0.0
            for o, e in [(o1, e1), (o2, e2), (autre1, e_autre1), (autre2, e_autre2)]:
                if o > 0 and e > 0:
                    g2 += o * math.log(o / e)
            g2 *= 2

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