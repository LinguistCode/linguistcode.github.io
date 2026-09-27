
### ---------------------
# Which words of a text appear in the NRC Emotion Intensity Lexicon (Mohammad 2018):
# Usage:
#   fear_lexicon.py --lexicon LEXIQUE.txt --corpus CORPUS.txt [--out resultats.tsv]
### ---------------------

import argparse # command-line arguments (--lexicon, --corpus, --out)
import re # regex, for the tokenisation
import sys # stdout / stderr streams
from collections import Counter # token counts in one line


### ---------------------
# Load the lexicon -> {word: score}. Tabs or spaces both accepted.
# Takes the FIRST column as the word and the LAST one as the score,
# so the full NRC file (word / emotion / score) keeps only the last emotion
# seen for a word -> feed it the fear-only file.
### ---------------------
def load_lexicon(path):
    lexicon = {}
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            parts = [p for p in parts if p != ""]  ### copes with double tabs
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
    # Simple tokenisation: runs of Unicode letters, lowercased (no digits, no "_").
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

    # Keep only the types that are in the lexicon: (word, frequency, score).
    matches = [
        (word, count, lexicon[word])
        for word, count in counts.items()
        if word in lexicon
    ]
    # Sort by frequency (descending), then alphabetically for ties.
    matches.sort(key=lambda x: (-x[1], x[0]))

    # Results go to the --out file if given, otherwise to the console.
    out = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout
    try:
        out.write("\n")
        out.write(f"{'mot':<15}{'occurrences':<15}{'score':<10}\n")
        for word, count, score in matches:
            out.write(f"{word:<15}{count:<15}{score:<10}\n")
    finally:
        if args.out:
            out.close()

    # Summary on stderr so it never ends up inside the --out file.
    total_tokens = len(tokens)
    total_matches = sum(c for _, c, _ in matches)
    print(file=sys.stderr)
    print(
        f"[info] {len(matches)} mots-clés trouvés dans le lexique "
        f"({total_matches} occurrences sur {total_tokens} tokens)",
        file=sys.stderr,
    )
    print("-" *30, file=sys.stderr) # visual separator to mark the end of the run

if __name__ == "__main__":
    main()
