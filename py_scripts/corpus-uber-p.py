import os
import re
import math
from scipy import stats

def calculate_uber_index(tokens):
    """Calcule l'Indice de Uber pour une liste de tokens."""
    n_tokens = len(tokens)
    if n_tokens <= 1:
        return 0
    
    n_types = len(set(tokens))
    if n_tokens == n_types:
        return 0 # Évite la division par zéro
        
    return (math.log(n_tokens)**2) / (math.log(n_tokens) - math.log(n_types))

def get_uber_scores_for_corpus(directory_path, chunk_size=10000):
    """
    Parcourt récursivement un dossier et tous ses sous-dossiers, 
    lit les fichiers .txt, concatène le texte, le divise en blocs 
    et calcule l'Indice de Uber.
    """
    all_tokens = []
    
    # 1. Parcours récursif de l'arborescence
    for root, dirs, files in os.walk(directory_path):
        for filename in files:
            if filename.endswith(".txt"):
                filepath = os.path.join(root, filename)
                
                # Sécurité pour éviter les plantages sur des fichiers spécifiques
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                        tokens = re.findall(r'\b\w+\b', text.lower())
                        all_tokens.extend(tokens)
                except Exception as e:
                    print(f"Erreur ignorée sur {filepath} : {e}")
                
    # 2. Découpage en blocs (chunking)
    scores = []
    # On ignore le dernier bloc s'il est incomplet
    for i in range(0, len(all_tokens) - chunk_size + 1, chunk_size):
        chunk = all_tokens[i:i + chunk_size]
        scores.append(calculate_uber_index(chunk))
        
    return scores

def main():
    # ---------------------------------------------------------
    # 1. Configuration des chemins
    # ---------------------------------------------------------
    path_bush = r"D:\Local_corpus\Bush"
    path_obama = r"D:\Local_corpus\Obama"
    path_trump = r"D:\Local_corpus\Trump"
    
    chunk_size = 10000 # Taille du bloc d'échantillonnage
    
    print(f"Génération des échantillons ({chunk_size} mots par bloc)...")
    scores_bush = get_uber_scores_for_corpus(path_bush, chunk_size)
    scores_obama = get_uber_scores_for_corpus(path_obama, chunk_size)
    scores_trump = get_uber_scores_for_corpus(path_trump, chunk_size)
    
    print(f"Blocs générés : Bush ({len(scores_bush)}), Obama ({len(scores_obama)}), Trump ({len(scores_trump)})\n")

    # ---------------------------------------------------------
    # 2. Test ANOVA (Analyse de variance globale)
    # ---------------------------------------------------------
    f_stat, p_value = stats.f_oneway(scores_bush, scores_obama, scores_trump)
    
    print("=== RÉSULTATS ANOVA ===")
    print(f"Statistique F : {f_stat:.4f}")
    print(f"Valeur p      : {p_value:.4e}")
    
    if p_value < 0.05:
        print("-> Différence globale significative. Lancement du test post-hoc...\n")
        
        # ---------------------------------------------------------
        # 3. Test Post-Hoc de Tukey (Comparaisons par paires)
        # ---------------------------------------------------------
        res = stats.tukey_hsd(scores_bush, scores_obama, scores_trump)
        
        print("=== COMPARAISONS PAR PAIRES (TUKEY HSD) ===")
        print("Groupes : 0=Bush, 1=Obama, 2=Trump")
        print(res)
    else:
        print("-> Aucune différence significative globale (p >= 0.05).")

if __name__ == "__main__":
    main()