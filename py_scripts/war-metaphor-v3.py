"""
==============================================================================
 ANALYSE DES EMPLOIS METAPHORIQUES DU CHAMP LEXICAL DE LA GUERRE
==============================================================================
Ce script part d'exports de concordancier (Sketch Engine) et classe chaque
occurrence en "littéral" / "métaphorique" / "ambigu" sur la base de marqueurs
lexicaux, d'un pattern syntaxique dynamique ("war on ___" / "fight against
___") et d'une heuristique morpho-lexicale pour les noms abstraits.

WORKFLOW EN DEUX ETAPES (important pour ta partie méthodo) :
  1) Lancer le script normalement (bloc __main__) -> il traite le(s)
     corpus, génère le classeur Excel avec un onglet "Inter_Annotator_Task"
     contenant une colonne "Manual_Annotation" VIDE.
  2) Toi (ou un second annotateur) remplissez cette colonne à la main avec
     "literal" / "metaphorical" / "ambiguous" pour chaque ligne.
  3) Tu relances ensuite evaluate_reliability(chemin_du_fichier_annote) qui
     recharge ce même onglet, compare Manual_Annotation (vérité terrain)
     à category (prédiction du script), et calcule accuracy, precision/
     recall/F1 par catégorie, ainsi que le kappa de Cohen. Un onglet
     "Reliability_Report" est ajouté au classeur.

Ce script ne dépend PAS de scikit-learn : les métriques sont recalculées
« à la main » à partir de la matrice de confusion, pour ne pas ajouter de
dépendance externe et pour que tu puisses vérifier les formules toi-même
dans ta thèse (annexe méthodo).

FORMATS DE CORPUS ACCEPTÉS EN ENTRÉE (détection automatique par extension) :
  - .xlsx / .xls : export KWIC Sketch Engine avec colonnes
      "Reference" / "Left" / "Kwic" / "Right" (le nom de corpus/locuteur
      est extrait automatiquement de la colonne Reference, ex.
      "doc#0,Trump/2016/..." -> "Trump", sauf si tu forces un nom via
      load_all_corpora()).
      Comme le mot-nœud réel (Kwic) est connu, la traçabilité gauche/
      droite se calcule par rapport à ce vrai nœud, et non plus par
      rapport au milieu artificiel de la phrase.
  - .txt : une phrase par ligne, ou export KWIC tabulé
      (left \\t node \\t right) sans le vrai index du nœud -> on retombe
      alors sur le milieu de la phrase comme pivot.
==============================================================================
"""

import re
import spacy
from spacy.matcher import Matcher
import pandas as pd
import numpy as np
import logging
import os
from datetime import datetime
from openpyxl import load_workbook

# ==========================================
# 0. VERSION DU SCRIPT
# ==========================================
# Change à chaque modification livrée. Affiché au démarrage (voir plus bas)
# pour vérifier facilement quelle version tu es en train d'exécuter.
SCRIPT_VERSION = "v3.2.5 (2026-07-13) - greater sample size"

# ==========================================
# 1. CONFIGURATION ET LOGGING
# ==========================================
log_filename = f"nlp_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logging.info(f"Démarrage du script d'analyse NLP — {SCRIPT_VERSION}")

# ==========================================
# 2. LEXIQUES ET CONTRÔLE DE CHEVAUCHEMENT
# ==========================================
LITERAL_MARKERS = {"army", "soldier", "weapon", "troop", "battlefield", "gun",
                    "combat", "tank", "bomb", "missile", "infantry", "warfare",
                    "casualty", "invasion", "artillery"}

METAPHORICAL_MARKERS = {"poverty", "drug", "disease", "cancer", "crime",
                         "inflation", "terror", "obesity", "corruption",
                         "addiction", "unemployment", "illiteracy", "racism",
                         "pandemic", "recession"}

# Liste curatée de noms abstraits fréquents dans ce type de discours
# (complète l'heuristique morphologique ci-dessous : un mot peut être
# abstrait sans porter un des suffixes listés, ex. "terror", "crime").
KNOWN_ABSTRACT_NOUNS = {
    "poverty", "terror", "terrorism", "drugs", "drug", "crime", "inflation",
    "obesity", "corruption", "addiction", "unemployment", "illiteracy",
    "racism", "hate", "hunger", "disease", "cancer", "pandemic", "recession",
    "ignorance", "injustice", "extremism", "radicalization", "misinformation",
    "fear", "violence", "inequality"
}

ABSTRACT_SUFFIXES = ("tion", "sion", "ism", "ity", "ment", "ness", "ance",
                      "ence", "acy", "hood", "dom")

# Détection de chevauchement (Sécurité méthodologique)
overlap = LITERAL_MARKERS.intersection(METAPHORICAL_MARKERS)
if overlap:
    logging.error(f"ERREUR CRITIQUE: Chevauchement détecté dans les lexiques: {overlap}")
    raise ValueError(f"Des termes apparaissent dans les deux listes : {overlap}")
else:
    logging.info("Contrôle des lexiques : OK. Aucun chevauchement détecté.")


def is_abstract_noun(lemma: str) -> bool:
    """
    Heuristique combinée pour juger si un nom est abstrait :
      1) appartenance à la liste curatée KNOWN_ABSTRACT_NOUNS
      2) sinon, heuristique morphologique par suffixe (-tion, -ism, -ity...)
    """
    lemma = lemma.lower()
    if lemma in KNOWN_ABSTRACT_NOUNS:
        return True
    return lemma.endswith(ABSTRACT_SUFFIXES)


# ==========================================
# 3. CHARGEMENT DE SPACY ET MATCHER
# ==========================================
logging.info("Chargement du modèle spaCy (en_core_web_sm)...")
nlp = spacy.load("en_core_web_sm", disable=["ner"])

matcher = Matcher(nlp.vocab)
# "war on X" / "fight against X" -> un ou plusieurs noms (groupe nominal simple)
pattern = [
    {"LEMMA": {"IN": ["war", "fight"]}},
    {"LOWER": {"IN": ["on", "against"]}},
    {"POS": {"IN": ["DET", "ADJ"]}, "OP": "*"},
    {"POS": "NOUN", "OP": "+"},
]
matcher.add("METAPHOR_TARGET", [pattern])


# ==========================================
# 4. TESTS DE RÉGRESSION
# ==========================================
def run_regression_tests():
    """
    Jeu de tests de non-régression. Toute modification des lexiques ou de
    l'heuristique doit être validée contre CES phrases avant d'être utilisée
    sur le corpus réel. Ajoute ici toute phrase qui t'a posé problème par le
    passé : c'est la meilleure garantie que l'analyse reste stable.
    """
    logging.info("Lancement des tests de régression...")
    test_cases = [
        # --- Cas littéraux ---
        ("The army fought a long battle.", "literal"),
        ("The soldier stood on the battlefield.", "literal"),
        ("The troops were equipped with new weapons.", "literal"),
        ("Tanks and artillery crossed the border.", "literal"),
        ("The gun was found near the camp.", "literal"),
        ("Heavy combat was reported near the front line.", "literal"),
        ("The invasion caused thousands of casualties.", "literal"),
        ("Soldiers carried their weapons across the battlefield.", "literal"),
        ("The warfare between the two armies intensified.", "literal"),
        ("The infantry advanced under artillery fire.", "literal"),

        # --- Cas métaphoriques (marqueurs lexicaux simples) ---
        ("We must win this war on poverty.", "metaphorical"),
        ("The war on drugs has failed for decades.", "metaphorical"),
        ("This is a fight against inflation.", "metaphorical"),
        ("The government declared war on corruption.", "metaphorical"),
        ("Doctors are fighting a war against cancer.", "metaphorical"),
        ("The war on terror reshaped foreign policy.", "metaphorical"),
        ("We are losing the fight against unemployment.", "metaphorical"),
        ("The war on obesity needs new strategies.", "metaphorical"),
        ("A fight against racism is long overdue.", "metaphorical"),
        ("The war on crime remains controversial.", "metaphorical"),
        ("It is a fight against addiction.", "metaphorical"),
        ("The war on illiteracy continues nationwide.", "metaphorical"),

        # --- Cas métaphoriques via pattern dynamique + suffixe abstrait ---
        ("They launched a war on extremism.", "metaphorical"),
        ("The war on misinformation is only beginning.", "metaphorical"),
        ("This is a fight against radicalization.", "metaphorical"),

        # --- Cas ambigus ---
        ("It is a fight.", "ambiguous"),
        ("The war continued for years.", "ambiguous"),
        ("They discussed the fight yesterday.", "ambiguous"),
        ("It was a difficult situation for everyone.", "ambiguous"),
        ("The meeting ended without conclusion.", "ambiguous"),
    ]

    failures = []
    for text, expected in test_cases:
        result = analyze_sentence(text, "test_corpus")
        if result is None or result['category'] != expected:
            failures.append((text, expected, result['category'] if result else None))

    if failures:
        for text, expected, obtained in failures:
            logging.error(f"Test échoué : '{text}' -> attendu={expected}, obtenu={obtained}")
        raise AssertionError(f"{len(failures)} test(s) de régression ont échoué. Voir le log.")

    logging.info(f"Tests de régression : OK ({len(test_cases)} phrases). Le modèle de classification est stable.")


# ==========================================
# 5. FONCTION D'ANALYSE PRINCIPALE
# ==========================================
def analyze_sentence(text, corpus_name, kwic_word=None, kwic_char_pos=None, reference=None):
    """
    kwic_word / kwic_char_pos : quand le texte provient d'un export KWIC
    Sketch Engine, le vrai mot-nœud (et si possible sa position exacte en
    caractères dans `text`) est connu. Dans ce cas, la traçabilité gauche/
    droite est calculée par rapport à CE nœud réel plutôt que par rapport
    au milieu artificiel de la phrase, ce qui rend la distance beaucoup
    plus significative pour l'analyse.
    reference : métadonnées du document source (colonne Reference de
    Sketch Engine), reportées telles quelles dans le résultat pour
    permettre de retrouver l'occurrence d'origine.
    """
    try:
        doc = nlp(text)

        score_lit = 0
        score_meta = 0
        traceability = []
        dynamic_targets = []

        # Détermination du nœud pivot :
        #  1) position exacte en caractères si fournie (cas xlsx Sketch Engine)
        #  2) sinon, recherche du mot kwic_word dans le texte
        #  3) sinon (txt sans nœud connu), repli sur le milieu de la phrase
        expected_pos = None
        if kwic_char_pos is not None:
            expected_pos = kwic_char_pos
        elif kwic_word:
            expected_pos = text.lower().find(kwic_word.lower())
            if expected_pos == -1:
                expected_pos = None

        node_token = None
        if expected_pos is not None and len(doc) > 0:
            for t in doc:
                if t.idx <= expected_pos < t.idx + len(t.text):
                    node_token = t
                    break
            if node_token is None:
                node_token = min(doc, key=lambda t: abs(t.idx - expected_pos))

        middle_index = node_token.i if node_token is not None else len(doc) // 2

        for token in doc:
            lemma = token.lemma_.lower()
            side = "left" if token.i < middle_index else "right"
            distance = abs(token.i - middle_index)

            if lemma in LITERAL_MARKERS:
                score_lit += 1
                traceability.append({"marker": lemma, "type": "literal", "side": side, "distance": distance})
            elif lemma in METAPHORICAL_MARKERS:
                score_meta += 1
                traceability.append({"marker": lemma, "type": "metaphorical", "side": side, "distance": distance})

        # Extraction dynamique (war on ___ / fight against ___)
        matches = matcher(doc)
        for match_id, start, end in matches:
            span = doc[start:end]
            target_noun = span[-1].lemma_.lower()
            target_side = "left" if span[-1].i < middle_index else "right"
            target_distance = abs(span[-1].i - middle_index)

            if is_abstract_noun(target_noun):
                score_meta += 2  # poids renforcé : structure syntaxique explicite
                dynamic_targets.append(target_noun)
                traceability.append({
                    "marker": f"dynamic:{target_noun}",
                    "type": "metaphorical",
                    "side": target_side,
                    "distance": target_distance
                })

        # Score de confiance normalisé, borné dans ]-1, 1[
        confidence_score = (score_meta - score_lit) / (score_meta + score_lit + 1)

        if confidence_score > 0:
            category = "metaphorical"
        elif confidence_score < 0:
            category = "literal"
        else:
            category = "ambiguous"

        return {
            "corpus": corpus_name,
            "reference": reference or "",
            "text": text,
            "kwic_node": kwic_word or "",
            "category": category,
            "confidence_score": round(confidence_score, 3),
            "dynamic_targets": ", ".join(dynamic_targets),
            "traceability": str(traceability)
        }

    except Exception as e:
        logging.error(f"Erreur lors de l'analyse de la phrase : '{str(text)[:60]}...' -> {str(e)}")
        return None


# ==========================================
# 6. CHARGEMENT DES CORPUS (exports Sketch Engine : .txt ou .xlsx)
# ==========================================
def _safe_str(value):
    """Convertit proprement une valeur de cellule (NaN, float, etc.) en str."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def extract_corpus_name_from_reference(reference):
    """
    Extrait le nom du locuteur/corpus depuis la colonne Reference d'un
    export Sketch Engine, ex. "doc#0,Trump/2016/T - 2016-07-21 - ..."
    -> "Trump". Utilisé seulement quand aucun corpus_name explicite n'est
    fourni (voir load_corpus_from_kwic_excel).
    """
    reference = _safe_str(reference)
    if not reference:
        return "unknown"
    match = re.search(r"doc#\d+,\s*([^/,]+)", reference)
    if match:
        return match.group(1).strip()
    for sep in ("/", ","):
        if sep in reference:
            return reference.split(sep)[0].strip()
    return reference[:30]


def _normalize_kwic_columns(df):
    """Renomme les colonnes vers les noms canoniques Reference/Left/Kwic/Right,
    insensible à la casse et aux espaces superflus."""
    canonical = {"reference": "Reference", "left": "Left", "kwic": "Kwic", "right": "Right"}
    rename_map = {col: canonical[str(col).strip().lower()]
                  for col in df.columns if str(col).strip().lower() in canonical}
    return df.rename(columns=rename_map)


def load_corpus_from_file(filepath, corpus_name=None, encoding="utf-8"):
    """
    Charge un export de concordancier au format texte (.txt).
    Gère deux formats courants, ligne par ligne, sans planter sur une ligne
    malformée (elle est loguée et ignorée, le traitement continue) :

      - Format "phrase simple" : une phrase par ligne.
      - Format KWIC tabulé : colonnes "left context \\t node \\t right
        context". Les 3 colonnes sont recollées en une seule phrase.
        NB : dans ce format texte, l'index exact du nœud n'est pas
        récupéré (contrairement au format .xlsx) ; la traçabilité
        gauche/droite retombe alors sur le milieu de la phrase.

    Retourne une liste de dicts {"corpus", "text", "kwic", "reference"}
    (kwic/reference = None pour ce format).
    """
    records = []
    if not os.path.exists(filepath):
        logging.error(f"Fichier introuvable, ignoré : {filepath}")
        return records

    try:
        with open(filepath, encoding=encoding, errors="replace") as f:
            for line_number, raw_line in enumerate(f, start=1):
                try:
                    line = raw_line.rstrip("\n").strip()
                    if not line:
                        continue

                    if line.lower().startswith(("left context", "concordance", "kwic")):
                        continue

                    if "\t" in line:
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            sentence = " ".join(p.strip() for p in parts[:3] if p.strip())
                        else:
                            sentence = " ".join(p.strip() for p in parts if p.strip())
                    else:
                        sentence = line

                    if sentence:
                        records.append({"corpus": corpus_name, "text": sentence, "kwic": None,
                                         "kwic_char_pos": None, "reference": None})

                except Exception as e:
                    logging.error(f"Ligne {line_number} malformée dans {filepath}, ignorée -> {str(e)}")
                    continue

    except Exception as e:
        logging.error(f"Impossible de lire le fichier {filepath} -> {str(e)}")

    logging.info(f"{len(records)} phrases chargées depuis {filepath}.")
    return records


def load_corpus_from_kwic_excel(filepath, corpus_name=None, sheet_name=0):
    """
    Charge un export KWIC Sketch Engine au format .xlsx, avec les colonnes
    "Reference" / "Left" / "Kwic" / "Right" (comme dans warmeta-test.xlsx).

    - Le mot-nœud (colonne Kwic) et sa position exacte en caractères dans
      le texte reconstitué (Left + Kwic + Right) sont conservés, pour que
      analyze_sentence() calcule la traçabilité gauche/droite par rapport
      au VRAI nœud plutôt que par rapport au milieu de la phrase.
    - Si corpus_name est fourni, il est utilisé pour toutes les lignes.
      Sinon, le nom de corpus est extrait automatiquement de la colonne
      Reference pour chaque ligne (utile si un même fichier mélange
      plusieurs locuteurs/années).
    - Chaque ligne malformée est loguée et ignorée sans interrompre le
      chargement du reste du fichier.

    Retourne une liste de dicts {"corpus", "text", "kwic", "kwic_char_pos",
    "reference"}.
    """
    records = []
    if not os.path.exists(filepath):
        logging.error(f"Fichier introuvable, ignoré : {filepath}")
        return records

    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
    except Exception as e:
        logging.error(f"Impossible de lire le fichier Excel {filepath} -> {str(e)}")
        return records

    df = _normalize_kwic_columns(df)
    required_cols = {"Left", "Kwic", "Right"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        logging.error(
            f"Colonnes manquantes dans {filepath} : {sorted(missing_cols)}. "
            "Format attendu (export KWIC Sketch Engine) : Reference / Left / Kwic / Right."
        )
        return records
    has_reference = "Reference" in df.columns

    for row_number, row in df.iterrows():
        try:
            left = _safe_str(row.get("Left"))
            kwic = _safe_str(row.get("Kwic"))
            right = _safe_str(row.get("Right"))
            reference = _safe_str(row.get("Reference")) if has_reference else ""

            if not kwic:
                logging.warning(f"Ligne {row_number} sans mot-nœud (Kwic) dans {filepath}, ignorée.")
                continue

            # Reconstruction du texte + position exacte du nœud (en caractères)
            parts = []
            if left:
                parts.append(left)
            kwic_char_pos = sum(len(p) + 1 for p in parts)  # +1 pour l'espace de jointure
            parts.append(kwic)
            if right:
                parts.append(right)
            text = " ".join(parts).strip()

            if not text:
                continue

            row_corpus = corpus_name if corpus_name else extract_corpus_name_from_reference(reference)

            records.append({
                "corpus": row_corpus,
                "text": text,
                "kwic": kwic,
                "kwic_char_pos": kwic_char_pos,
                "reference": reference
            })

        except Exception as e:
            logging.error(f"Ligne {row_number} malformée dans {filepath}, ignorée -> {str(e)}")
            continue

    logging.info(f"{len(records)} occurrences KWIC chargées depuis {filepath}.")
    return records


def load_corpus(filepath, corpus_name=None):
    """
    Dispatcher générique : choisit le bon loader selon l'extension du
    fichier (.xlsx/.xls -> export KWIC Sketch Engine, sinon -> .txt).
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".xlsx", ".xls"):
        return load_corpus_from_kwic_excel(filepath, corpus_name=corpus_name)
    return load_corpus_from_file(filepath, corpus_name=corpus_name)


# ==========================================
# 7. ÉCHANTILLONNAGE ET TRAITEMENT
# ==========================================
def process_corpus(records, corpus_name):
    """
    records : liste de dicts (voir load_corpus*) OU liste de phrases (str),
    pour rester compatible avec un usage direct/ad hoc.
    """
    results = []
    for idx, record in enumerate(records):
        if idx % 50 == 0 and idx > 0:
            logging.info(f"Traitement {corpus_name} : {idx} occurrences analysées...")

        try:
            if isinstance(record, dict):
                text = record.get("text", "")
                kwic = record.get("kwic")
                kwic_char_pos = record.get("kwic_char_pos")
                reference = record.get("reference")
                final_corpus = record.get("corpus") or corpus_name
            else:
                text = record
                kwic = kwic_char_pos = reference = None
                final_corpus = corpus_name

            res = analyze_sentence(text, final_corpus, kwic_word=kwic,
                                    kwic_char_pos=kwic_char_pos, reference=reference)
            if res:
                results.append(res)
        except Exception as e:
            # Filet de sécurité supplémentaire : une occurrence corrompue ne
            # doit jamais interrompre le traitement du corpus.
            logging.error(f"Échec inattendu sur l'occurrence #{idx} du corpus {corpus_name}, ignorée -> {str(e)}")
            continue

    return results


def generate_exports(df, sample_size=30, output_path=None):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_path = output_path or f"NLP_Results_{timestamp}.xlsx"

    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        # Onglet 1 : données brutes
        df.to_excel(writer, sheet_name='All_Data', index=False)

        # Onglet 2 : échantillonnage stratifié pour annotation manuelle
        logging.info("Génération de l'échantillon stratifié...")
        stratified_parts = []
        for cat, group in df.groupby('category'):
            n = min(len(group), sample_size)
            stratified_parts.append(group.sample(n=n, random_state=42))
        stratified_sample = pd.concat(stratified_parts, ignore_index=True) if stratified_parts else df.iloc[0:0].copy()
        stratified_sample.insert(0, 'Manual_Annotation', '')
        stratified_sample.to_excel(writer, sheet_name='Inter_Annotator_Task', index=False)

        # Onglet 3 : fréquence des cibles métaphoriques par corpus
        logging.info("Génération du tableau croisé des cibles...")
        df_targets = df[df['dynamic_targets'] != ""]
        if not df_targets.empty:
            df_exploded = df_targets.assign(
                dynamic_targets=df_targets['dynamic_targets'].str.split(', ')
            ).explode('dynamic_targets').reset_index(drop=True)
            # reset_index(drop=True) est indispensable : dès qu'une occurrence a
            # PLUSIEURS cibles dynamiques (ex. "poverty, terror"), .explode() duplique
            # l'index d'origine, et pd.crosstab(..., margins=True) échoue ensuite avec
            # "cannot reindex on an axis with duplicate labels" sur un axe non-unique.
            freq_table = pd.crosstab(df_exploded['dynamic_targets'], df_exploded['corpus'], margins=True)
            freq_table.to_excel(writer, sheet_name='Metaphor_Targets_Freq')
        else:
            pd.DataFrame({"Message": ["Aucune cible dynamique trouvée"]}).to_excel(
                writer, sheet_name='Metaphor_Targets_Freq'
            )

    logging.info(f"Export Excel terminé avec succès : {excel_path}")
    return excel_path


# ==========================================
# 8. FIABILITÉ INTER-ANNOTATEUR (precision/recall/accord)
# ==========================================
def _confusion_counts(y_true, y_pred, labels):
    """Construit la matrice de confusion sous forme de dict {(true, pred): n}."""
    counts = {(t, p): 0 for t in labels for p in labels}
    for t, p in zip(y_true, y_pred):
        if t in labels and p in labels:
            counts[(t, p)] += 1
    return counts


def _cohen_kappa(counts, labels, n):
    """Kappa de Cohen calculé à la main à partir de la matrice de confusion."""
    po = sum(counts[(l, l)] for l in labels) / n

    row_totals = {l: sum(counts[(l, p)] for p in labels) for l in labels}   # vérité terrain
    col_totals = {l: sum(counts[(t, l)] for t in labels) for l in labels}   # prédiction du script

    pe = sum((row_totals[l] / n) * (col_totals[l] / n) for l in labels)

    if pe == 1:
        return 1.0
    return (po - pe) / (1 - pe)


def evaluate_reliability(annotated_excel_path, sheet_name="Inter_Annotator_Task", report_excel_path=None):
    """
    À appeler APRES avoir rempli manuellement la colonne 'Manual_Annotation'
    dans l'onglet Inter_Annotator_Task du classeur généré par generate_exports().

    Compare :
      - 'category'          -> prédiction automatique du script
      - 'Manual_Annotation' -> vérité terrain (ton annotation manuelle)

    Calcule : accuracy globale, precision/recall/F1 par catégorie, et le
    kappa de Cohen (accord au-delà du hasard). Ajoute un onglet
    'Reliability_Report' au classeur (ou à report_excel_path si fourni),
    et renvoie un dict avec toutes les métriques pour ta partie méthodo.
    """
    logging.info(f"Évaluation de la fiabilité à partir de : {annotated_excel_path}")

    df = pd.read_excel(annotated_excel_path, sheet_name=sheet_name)

    df['Manual_Annotation'] = df['Manual_Annotation'].astype(str).str.strip().str.lower()
    missing_mask = ~df['Manual_Annotation'].isin(["literal", "metaphorical", "ambiguous"])
    n_missing = missing_mask.sum()
    if n_missing > 0:
        logging.warning(
            f"{n_missing} ligne(s) sans annotation manuelle valide (vide ou hors des 3 catégories) "
            "seront exclues du calcul de fiabilité."
        )
    df_valid = df[~missing_mask].copy()

    if df_valid.empty:
        raise ValueError(
            "Aucune ligne annotée manuellement valide trouvée. "
            "Remplis la colonne 'Manual_Annotation' avec 'literal', 'metaphorical' ou 'ambiguous' avant d'évaluer."
        )

    labels = ["literal", "metaphorical", "ambiguous"]
    y_true = df_valid['Manual_Annotation'].tolist()
    y_pred = df_valid['category'].tolist()
    n = len(y_true)

    counts = _confusion_counts(y_true, y_pred, labels)

    accuracy = sum(counts[(l, l)] for l in labels) / n

    per_class = {}
    for l in labels:
        tp = counts[(l, l)]
        fp = sum(counts[(t, l)] for t in labels if t != l)   # prédit l, vérité != l
        fn = sum(counts[(l, p)] for p in labels if p != l)   # vérité l, prédit != l

        precision = tp / (tp + fp) if (tp + fp) > 0 else float('nan')
        recall = tp / (tp + fn) if (tp + fn) > 0 else float('nan')
        if precision + recall > 0 and not (np.isnan(precision) or np.isnan(recall)):
            f1 = 2 * precision * recall / (precision + recall)
        else:
            f1 = float('nan')

        support = sum(counts[(l, p)] for p in labels)  # nb réel d'occurrences de cette classe (vérité terrain)
        per_class[l] = {"precision": precision, "recall": recall, "f1": f1, "support": support}

    kappa = _cohen_kappa(counts, labels, n)

    logging.info(f"Fiabilité calculée sur {n} lignes annotées : accuracy={accuracy:.3f}, kappa de Cohen={kappa:.3f}")

    # --- Construction des tableaux pour l'export ---
    confusion_df = pd.DataFrame(
        [[counts[(t, p)] for p in labels] for t in labels],
        index=[f"Vérité: {l}" for l in labels],
        columns=[f"Prédit: {l}" for l in labels]
    )

    metrics_df = pd.DataFrame(per_class).T
    metrics_df.index.name = "category"

    summary_df = pd.DataFrame({
        "metric": ["n_lignes_evaluees", "n_lignes_exclues_sans_annotation", "accuracy_globale", "kappa_de_cohen"],
        "value": [n, int(n_missing), round(accuracy, 4), round(kappa, 4)]
    })

    target_path = report_excel_path or annotated_excel_path
    book = load_workbook(target_path) if os.path.exists(target_path) and target_path == annotated_excel_path else None

    with pd.ExcelWriter(
        target_path,
        engine='openpyxl',
        mode='a' if book is not None else 'w',
        if_sheet_exists='replace' if book is not None else None
    ) as writer:
        summary_df.to_excel(writer, sheet_name='Reliability_Report', index=False, startrow=0)
        confusion_df.to_excel(writer, sheet_name='Reliability_Report', startrow=len(summary_df) + 3)
        metrics_df.to_excel(writer, sheet_name='Reliability_Report', startrow=len(summary_df) + len(confusion_df) + 7)

    logging.info(f"Rapport de fiabilité ajouté au classeur : {target_path} (onglet 'Reliability_Report')")

    return {
        "n": n,
        "n_excluded": int(n_missing),
        "accuracy": accuracy,
        "cohen_kappa": kappa,
        "per_class": per_class,
        "confusion_matrix": confusion_df,
    }


# ==========================================
# 9. LANCEMENT DU PROGRAMME
# ==========================================
def load_all_corpora(corpus_files):
    """
    corpus_files : dict {nom_du_corpus: chemin_du_fichier} — le fichier peut
    être un .txt (une phrase par ligne ou KWIC tabulé) OU un .xlsx (export
    KWIC Sketch Engine avec colonnes Reference/Left/Kwic/Right) ; le format
    est détecté automatiquement par extension (voir load_corpus()).
    Le nom_du_corpus (la clé du dict) est appliqué à toutes les lignes du
    fichier, qu'il s'agisse de .txt ou de .xlsx.

    Retourne un dict {nom_du_corpus: [liste de records]}.
    Si un fichier est absent ou vide, le corpus correspondant est ignoré
    (loggé en warning) plutôt que de faire planter tout le script.

    Cas particulier : si un même fichier .xlsx mélange plusieurs locuteurs
    et que tu veux laisser le script détecter le corpus ligne à ligne à
    partir de la colonne Reference, utilise directement
    load_corpus_from_kwic_excel(chemin, corpus_name=None) plutôt que ce
    dict (voir docstring de cette fonction).
    """
    corpora = {}
    for name, path in corpus_files.items():
        records = load_corpus(path, corpus_name=name)
        if records:
            corpora[name] = records
        else:
            logging.warning(f"Corpus '{name}' vide ou illisible ({path}) — ignoré.")
    return corpora


if __name__ == "__main__":
    # 1. Tests de sécurité
    run_regression_tests()

    # 2. Chargement des corpus.
    #    -> Remplace ces chemins par tes exports Sketch Engine réels :
    #       .txt (une phrase par ligne) ou .xlsx (export KWIC avec colonnes
    #       Reference/Left/Kwic/Right) sont tous les deux acceptés, détectés
    #       automatiquement par extension.
    #    -> Si les fichiers n'existent pas, on retombe sur des données de
    #       démonstration pour que le script reste exécutable tel quel.
    CORPUS_FILES = {
        "Bush": "KWIC-war-BUSH.xlsx",
        "Obama": "KWIC-war-OBAMA.xlsx",
        "Trump": "KWIC-war-TRUMP.xlsx",   
    }

    corpora = load_all_corpora(CORPUS_FILES)

    if not corpora:
        logging.warning("Aucun fichier de corpus trouvé sur disque : utilisation des données de démonstration.")
        corpora = {
            "Bush": [
                "We will win the war on terror.",
                "The soldier stood on the battlefield.",
                "This is a fight against poverty and disease.",
            ],
            "Obama": [
                "We must end the war on drugs.",
                "Our troops are returning home.",
                "The fight for equality continues.",
            ],
            "Trump": [
                "We are fighting a war on the invisible enemy.",
                "Our beautiful military is ready.",
                "It is a tough fight against crime.",
            ],
        }

    # 3. Traitement
    all_results = []
    for corpus_name, sentences in corpora.items():
        all_results.extend(process_corpus(sentences, corpus_name))

    # 4. Export
    df_results = pd.DataFrame(all_results)
    excel_path = generate_exports(df_results, sample_size=20)

    logging.info("Processus complet terminé.")
    logging.info(
        f"ÉTAPE SUIVANTE : ouvre '{excel_path}', remplis la colonne 'Manual_Annotation' "
        "dans l'onglet Inter_Annotator_Task, puis appelle "
        f"evaluate_reliability('{excel_path}') pour obtenir accuracy / precision / recall / kappa."
    )
