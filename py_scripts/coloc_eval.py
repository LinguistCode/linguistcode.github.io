### ---------------------
# Step 1: automatic valence (+ dominant emotion) of each collocation in an .xlsx file (collocations in column A).
#   Valence -> VADER first; if VADER knows none of the words, SentiWordNet.
#   Emotion -> NRCLex (secondary, optional).
# Results written in columns H (Valence) and I (Émotion) of a NEW file.
# Step 2 = coloc_eval_kappa.py, to check these labels against my manual ones.
### ---------------------

import sys
import re
import openpyxl
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

### ---------------------
### NLTK resources: silent, best-effort download (already there -> nothing happens)
### ---------------------
import nltk
for _res in ("punkt", "punkt_tab", "wordnet", "omw-1.4", "sentiwordnet",
             "averaged_perceptron_tagger", "averaged_perceptron_tagger_eng"):
    try:
        nltk.download(_res, quiet=True)
    except Exception:
        pass

from nltk import pos_tag
from nltk.corpus import wordnet as wn
from nltk.corpus import sentiwordnet as swn
from nltk.stem import WordNetLemmatizer

LEMMATIZER = WordNetLemmatizer()

### ---------------------
### Emotion = secondary, NRCLex is optional: the script still runs without it.
### ---------------------
try:
    from nrclex import NRCLex
    NRCLEX_OK = True
except ImportError:
    NRCLEX_OK = False

### ---------------------
### SETTINGS
### ---------------------
COLONNE_ENTREE = 1      ### A: collocation
COLONNE_VALENCE = 8     ### H
COLONNE_EMOTION = 9     ### I

### Thresholds recommended by the VADER authors for the "compound" score.
### Reused for SentiWordNet since its scale is comparable (-1..+1).
SEUIL_POSITIF = 0.05
SEUIL_NEGATIF = -0.05

### NRC emotion labels -> French labels written in the file.
EMOTIONS_FR = {
    "fear": "Peur", "anger": "Colère", "anticip": "Anticipation",
    "anticipation": "Anticipation", "trust": "Confiance", "surprise": "Surprise",
    "sadness": "Tristesse", "disgust": "Dégoût", "joy": "Joie",
}


def extraire_mots(texte):
    ### Basic tokenisation: runs of ASCII letters/apostrophes, lowercased.
    return re.findall(r"[a-zA-Z']+", str(texte).lower())


def treebank_vers_wordnet(tag):
    ### NLTK POS tag (Penn Treebank) -> WordNet constant. None = not a content word.
    if tag.startswith("J"):
        return wn.ADJ
    if tag.startswith("V"):
        return wn.VERB
    if tag.startswith("N"):
        return wn.NOUN
    if tag.startswith("R"):
        return wn.ADV
    return None


def score_sentiwordnet(texte):
    ### ---------------------
    ### Fallback valence with SentiWordNet, averaged over the recognised words.
    ### Each word: lemmatised, then FIRST WordNet sense = most frequent one,
    ### score = pos_score - neg_score (-1..+1, objectivity pulls it towards 0).
    ### None if no word is recognised at all.
    ### ---------------------
    mots = extraire_mots(texte)
    if not mots:
        return None
    try:
        tags = pos_tag(mots)
    except Exception:
        tags = [(m, "NN") for m in mots]  ### fallback: treat everything as a noun

    scores = []
    for mot, tag in tags:
        wn_pos = treebank_vers_wordnet(tag)
        if wn_pos is None:
            continue
        try:
            lemme = LEMMATIZER.lemmatize(mot, pos=wn_pos)
            synsets = list(swn.senti_synsets(lemme, wn_pos))
        except Exception:
            synsets = []
        if not synsets:
            continue
        sens_principal = synsets[0]  ### most frequent sense in WordNet
        scores.append(sens_principal.pos_score() - sens_principal.neg_score())

    if not scores:
        return None
    return sum(scores) / len(scores)


def analyser_valence(texte, analyzer):
    ### ---------------------
    ### Returns (label, score, source).
    ### label: "Positif" / "Négatif" / "Neutre" / "Non trouvé".
    ### source: "VADER" or "SentiWordNet" (None if "Non trouvé").
    ### VADER only if at least one word is in its lexicon; otherwise its
    ### compound = 0 would pass for "Neutre" when it really means "unknown".
    ### ---------------------
    mots = extraire_mots(texte)
    mots_connus_vader = [m for m in mots if m in analyzer.lexicon]

    if mots_connus_vader:
        compound = analyzer.polarity_scores(str(texte))["compound"]
        source = "VADER"
    else:
        compound = score_sentiwordnet(texte)
        source = "SentiWordNet"

    if compound is None:
        return "Non trouvé", None, None

    if compound >= SEUIL_POSITIF:
        label = "Positif"
    elif compound <= SEUIL_NEGATIF:
        label = "Négatif"
    else:
        label = "Neutre"

    return label, compound, source


def analyser_emotion(texte):
    ### Dominant emotion according to NRCLex (secondary analysis, best-effort).
    if not NRCLEX_OK:
        return "N/A (nrclex non installé)"
    try:
        obj = NRCLex(str(texte))
        ### positive/negative are valence, not emotions -> left out.
        freqs = {k: v for k, v in obj.affect_frequencies.items()
                 if k not in ("positive", "negative") and v > 0}

        if not freqs:
            ### Fallback: retry with lemmas, which sometimes match the NRC
            ### lexicon better than the inflected forms.
            mots = extraire_mots(texte)
            try:
                tags = pos_tag(mots)
            except Exception:
                tags = [(m, "NN") for m in mots]
            lemmes = []
            for mot, tag in tags:
                wn_pos = treebank_vers_wordnet(tag) or wn.NOUN
                try:
                    lemmes.append(LEMMATIZER.lemmatize(mot, pos=wn_pos))
                except Exception:
                    lemmes.append(mot)
            obj2 = NRCLex(" ".join(lemmes))
            freqs = {k: v for k, v in obj2.affect_frequencies.items()
                     if k not in ("positive", "negative") and v > 0}

        if not freqs:
            return "Aucune"
        ### Highest frequency wins (ties: first one met).
        top = max(freqs, key=freqs.get)
        return EMOTIONS_FR.get(top, top.capitalize())
    except Exception:
        return "Indéterminée"


def main(fichier_entree, fichier_sortie):
    wb = openpyxl.load_workbook(fichier_entree)
    ws = wb.active
    analyzer = SentimentIntensityAnalyzer()

    ### Just a warning if column A is not the collocation column: the run goes on anyway.
    entete = ws.cell(row=1, column=COLONNE_ENTREE).value
    if not entete or "collocation" not in str(entete).lower():
        print(f"Avertissement : la colonne 1 s'intitule '{entete}', pas "
              f"'collocation'. Poursuite sur la colonne 1 telle quelle.")

    ws.cell(row=1, column=COLONNE_VALENCE, value="Valence")
    ws.cell(row=1, column=COLONNE_EMOTION, value="Émotion")

    total = positifs = negatifs = neutres = non_trouves = 0
    par_source = {"VADER": 0, "SentiWordNet": 0}

    ### ---------------------
    ### ROW LOOP (row 1 = header)
    ### ---------------------
    for row in range(2, ws.max_row + 1):
        collocation = ws.cell(row=row, column=COLONNE_ENTREE).value
        if collocation is None or str(collocation).strip() == "":
            continue

        total += 1
        label, score, source = analyser_valence(collocation, analyzer)
        emotion = analyser_emotion(collocation)

        ### Cell format "Positif (+0.620, VADER)" -> coloc_eval_kappa.py knows how to read it back.
        if label == "Non trouvé":
            non_trouves += 1
            valeur_cellule = "Non trouvé"
        else:
            valeur_cellule = f"{label} ({score:+.3f}, {source})"
            par_source[source] += 1
            if label == "Positif":
                positifs += 1
            elif label == "Négatif":
                negatifs += 1
            else:
                neutres += 1

        ws.cell(row=row, column=COLONNE_VALENCE, value=valeur_cellule)
        ws.cell(row=row, column=COLONNE_EMOTION, value=emotion)

    ### Saved under a NEW name -> the input file is never overwritten.
    wb.save(fichier_sortie)

    ### ---------------------
    ### CONSOLE SUMMARY
    ### ---------------------
    print(f"Terminé : {fichier_sortie}")
    print(f"  Lignes analysées : {total}")
    print(f"  Positif / Négatif / Neutre : {positifs} / {negatifs} / {neutres}")
    if total:
        print(f"  Non trouvées (ni VADER ni SentiWordNet) : {non_trouves} "
              f"({non_trouves / total * 100:.1f} %)")
        print(f"  Trouvées via VADER : {par_source['VADER']} | "
              f"via SentiWordNet : {par_source['SentiWordNet']}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage : python analyse_valence_collocations.py entree.xlsx sortie.xlsx")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
