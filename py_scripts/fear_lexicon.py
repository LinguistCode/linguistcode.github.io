
# Pour trouver quels mots d'un texte sont présents dans le NRC Emotion Intensity Lexicon de Mohammad (2018) : https://saifmohammad.com/WebPages/AffectIntensity.htm
#Usage:
#    fear_lexicon.py --lexicon LEXIQUE.txt --corpus CORPUS.txt [--out resultats.tsv]

import argparse # module pour analyser les arguments passés CLI
import re # module pour les regex (ici pour la tokenisation)
import sys # module pour les flux d'entrée/sortie (ici pour stderr et stdout)
from collections import Counter # classe qui permet de compter les occurrences d'éléments dans un itérable (ici les tokens du corpus)


def load_lexicon(path): # charge le fichier lexique du NRCEIL, récupère les mots et leurs scores. Accepte tabulations ou espaces comme séparateurs. 
    lexicon = {}
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            parts = [p for p in parts if p != ""]  # gère les doubles tabulations
            if len(parts) < 2:
                parts = line.split()
            if len(parts) < 2:
                print(f"[avertissement] ligne {lineno} ignorée (format invalide): {line!r}",
                      file=sys.stderr)
                continue
            word, score = parts[0], parts[-1]
            try:
                score = float(score)
            except ValueError:
                print(f"[avertissement] ligne {lineno} ignorée (score non numérique): {line!r}",
                      file=sys.stderr)
                continue
            lexicon[word.lower()] = score
    return lexicon


def tokenize(text):
    #Tokenisation simple: suites de lettres (Unicode), minuscules.
    return re.findall(r"[^\W\d_]+", text.lower(), re.UNICODE)


def main():
    parser = argparse.ArgumentParser(description="Recherche de mots du texte dans un lexique.")
    parser.add_argument("--lexicon", required=True, help="Fichier lexique (mot\\tscore)")
    parser.add_argument("--corpus", required=True, help="Fichier texte (texte brut)")
    parser.add_argument("--out", default=None, help="Fichier de sortie TSV (défaut: stdout)")
    args = parser.parse_args()

    lexicon = load_lexicon(args.lexicon)

    with open(args.corpus, encoding="utf-8") as f:
        text = f.read()
    tokens = tokenize(text)
    counts = Counter(tokens)

    matches = [
        (word, count, lexicon[word])
        for word, count in counts.items()
        if word in lexicon
    ]
    # tri par fréquence décroissante, puis alphabétique 
    matches.sort(key=lambda x: (-x[1], x[0]))

    out = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout
    try:
        out.write("\n")
        out.write(f"{'mot':<15}{'occurrences':<15}{'score':<10}\n")
        for word, count, score in matches:
            out.write(f"{word:<15}{count:<15}{score:<10}\n")
    finally:
        if args.out:
            out.close()

    total_tokens = len(tokens)
    total_matches = sum(c for _, c, _ in matches)
    print(file=sys.stderr)
    print(
        f"[info] {len(matches)} mots-clés trouvés dans le lexique "
        f"({total_matches} occurrences sur {total_tokens} tokens)",
        file=sys.stderr,
    )
    print("-" *30, file=sys.stderr) # séparateur visiuel pour bien marquer la fin du programme

if __name__ == "__main__":
    main()
