### ---------------------
# Is lexical richness (Uber index) really different between Bush, Obama and Trump?
# One global U per president gives no variance, so no test is possible.
# We need to cut each corpus into fixed-size blocks, get one U per block, then compare the three distributions (ANOVA + Tukey HSD).
### ---------------------

import os
import re
import math
from scipy import stats

def calculate_uber_index(tokens):
    # Uber index for one list of tokens (natural log).
    n_tokens = len(tokens)
    if n_tokens <= 1:
        return 0
    
    n_types = len(set(tokens))
    if n_tokens == n_types:
        return 0 ### tokens == types -> denominator would be 0
        
    return (math.log(n_tokens)**2) / (math.log(n_tokens) - math.log(n_types))

def get_uber_scores_for_corpus(directory_path, chunk_size=10000):
    ### ---------------------
    # Walk the folder AND all its subfolders, read every .txt, glue all the
    # tokens together, cut them into blocks of chunk_size, one U per block.
    ### ---------------------
    all_tokens = []
    
    ### 1. Recursive walk through the year subfolders
    for root, dirs, files in os.walk(directory_path):
        for filename in files:
            if filename.endswith(".txt"):
                filepath = os.path.join(root, filename)
                
                # errors='ignore' + try/except: one broken file must not kill the whole run.
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                        # \w+ keeps digits too (unlike corpus-profile-maker) -> figures not directly comparable.
                        tokens = re.findall(r'\b\w+\b', text.lower())
                        all_tokens.extend(tokens)
                except Exception as e:
                    print(f"Erreur ignorée sur {filepath} : {e}")
                
    ### 2. Chunking
    scores = []
    # The last block is dropped if it is shorter than chunk_size:
    # U depends on text length, so every block must have the same size.
    for i in range(0, len(all_tokens) - chunk_size + 1, chunk_size):
        chunk = all_tokens[i:i + chunk_size]
        scores.append(calculate_uber_index(chunk))
        
    return scores

def main():
    ### ---------------------
    # 1. PATHS
    ### ---------------------
    path_bush = r"D:\Local_corpus\Bush"
    path_obama = r"D:\Local_corpus\Obama"
    path_trump = r"D:\Local_corpus\Trump"
    
    chunk_size = 10000 # block size (tokens) = one observation for the tests
    
    print(f"Génération des échantillons ({chunk_size} mots par bloc)...")
    scores_bush = get_uber_scores_for_corpus(path_bush, chunk_size)
    scores_obama = get_uber_scores_for_corpus(path_obama, chunk_size)
    scores_trump = get_uber_scores_for_corpus(path_trump, chunk_size)
    
    print(f"Blocs générés : Bush ({len(scores_bush)}), Obama ({len(scores_obama)}), Trump ({len(scores_trump)})\n")

    ### ---------------------
    # 2. ONE-WAY ANOVA (is there ANY difference between the three?)
    ### ---------------------
    f_stat, p_value = stats.f_oneway(scores_bush, scores_obama, scores_trump)
    
    print("=== RÉSULTATS ANOVA ===")
    print(f"Statistique F : {f_stat:.4f}")
    print(f"Valeur p      : {p_value:.4e}")
    
    if p_value < 0.05:
        print("-> Différence globale significative. Lancement du test post-hoc...\n")
        
        ### ---------------------
        # 3. TUKEY HSD POST-HOC (which pairs actually differ?) Only worth running if the ANOVA is significant.
        ### ---------------------
        res = stats.tukey_hsd(scores_bush, scores_obama, scores_trump)
        
        print("=== COMPARAISONS PAR PAIRES (TUKEY HSD) ===")
        print("Groupes : 0=Bush, 1=Obama, 2=Trump")
        print(res)
    else:
        print("-> Aucune différence significative globale (p >= 0.05).")

if __name__ == "__main__":
    main()