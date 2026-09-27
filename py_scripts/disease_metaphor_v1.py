### ---------------------
### METAPHORICAL USES OF THE DISEASE LEXICAL FIELD
### ---------------------
### Adapted from war_metaphor_v3.py: same pipeline, but the source domain is
### DISEASE instead of WAR. Takes concordance exports (Sketch Engine) and labels
### each hit "literal" / "metaphorical" / "ambiguous" from:
###   - lexical markers,
###   - a dynamic syntactic pattern ("the cancer/disease/virus/plague/epidemic...
###     of ___" / "infected/plagued/sickened/poisoned/afflicted by ___"),
###   - a morpho-lexical heuristic for abstract nouns.

### Logic (mirror of the war version):
###   - Source-domain trigger words (cancer, disease, virus, plague, epidemic,
###     sickness, illness, infection; infect, sicken, poison, afflict) are NOT
###     counted as markers, on purpose: like "war"/"fight" in the previous
###     version, they occur in literal (real clinical) AND metaphorical uses,
###     so on their own they discriminate nothing.
###   - LITERAL_MARKERS = concrete clinical vocabulary (patient, hospital,
###     doctor...) -> the context really is medical.
###   - METAPHORICAL_MARKERS = abstract social/political evils (corruption,
###     racism, extremism...) = the usual targets of disease metaphors in
###     presidential speech ("the cancer of corruption", "infected by division").

### TWO-STEP WORKFLOW (matters for the methodology chapter):
###   1) Run the script (__main__ block) -> processes the corpus/corpora and
###      writes the Excel workbook, with an "Inter_Annotator_Task" sheet whose
###      "Manual_Annotation" column is EMPTY.
###   2) Fill that column by hand (me, or a second annotator) with
###      "literal" / "metaphorical" / "ambiguous" for every row.
###   3) Call evaluate_reliability(path_to_annotated_file): it reloads that
###      sheet, compares Manual_Annotation (ground truth) with category (the
###      script's prediction), computes accuracy, precision/recall/F1 per
###      category and Cohen's kappa, and adds a "Reliability_Report" sheet.

### No scikit-learn on purpose: the metrics are recomputed by hand from the
### confusion matrix -> one dependency less, and every formula can be checked
### for the methodology appendix.

### INPUT FORMATS (picked from the file extension):
###   - .xlsx / .xls: Sketch Engine KWIC export, columns "Reference" / "Left" /
###     "Kwic" / "Right". The corpus/speaker name is read from Reference
###     (e.g. "doc#0,Trump/2016/..." -> "Trump") unless forced through
###     load_all_corpora(). The real node word (Kwic) is known, so left/right
###     traceability is measured from that node, not from the artificial
###     middle of the sentence.
###   - .txt: one sentence per line, or tab-separated KWIC (left \t node \t right)
###     without the node index -> falls back on the middle of the sentence.
### ---------------------

import re
import spacy
from spacy.matcher import Matcher
import pandas as pd
import numpy as np
import logging
import os
from datetime import datetime
from openpyxl import load_workbook

### ---------------------
### 0. SCRIPT VERSION
### ---------------------
### Bump it at every delivered change. Printed at start-up (see below) so I
### always know which version produced a given output.
SCRIPT_VERSION = "v1.0.0 (2026-07-14) - adaptation domaine MALADIE (base war_metaphor_v3.2.5)"

### ---------------------
### 1. CONFIG + LOGGING (one timestamped log file per run + console)
### ---------------------
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

### ---------------------
### 2. LEXICONS + OVERLAP CHECK
### ---------------------
LITERAL_MARKERS = {"patient", "hospital", "doctor", "nurse", "vaccine",
                    "symptom", "diagnosis", "treatment", "surgery",
                    "medication", "clinic", "physician", "prescription",
                    "ward", "quarantine"}

METAPHORICAL_MARKERS = {"corruption", "racism", "hatred", "extremism",
                         "crime", "poverty", "violence", "division",
                         "ignorance", "greed", "inequality", "terrorism",
                         "misinformation", "radicalization", "partisanship",
                         "prejudice"}

### Hand-picked abstract nouns that are frequent in this kind of discourse.
### Complements the suffix heuristic below: a noun can be abstract without any
### of the listed suffixes ("greed", "crime", "hatred", "poverty"...).
KNOWN_ABSTRACT_NOUNS = {
    "corruption", "racism", "extremism", "terrorism", "radicalization",
    "misinformation", "division", "inequality", "violence", "ignorance",
    "greed", "hatred", "hate", "prejudice", "partisanship", "injustice",
    "crime", "poverty", "apathy", "complacency", "distrust", "polarization",
    "intolerance", "fear", "dysfunction"
}

ABSTRACT_SUFFIXES = ("tion", "sion", "ism", "ity", "ment", "ness", "ance",
                      "ence", "acy", "hood", "dom")

### Methodological safety net: a word in BOTH lists would count for both sides
### -> stop the whole run before any analysis.
overlap = LITERAL_MARKERS.intersection(METAPHORICAL_MARKERS)
if overlap:
    logging.error(f"ERREUR CRITIQUE: Chevauchement détecté dans les lexiques: {overlap}")
    raise ValueError(f"Des termes apparaissent dans les deux listes : {overlap}")
else:
    logging.info("Contrôle des lexiques : OK. Aucun chevauchement détecté.")


def is_abstract_noun(lemma: str) -> bool:
    ### Combined heuristic to decide whether a noun is abstract:
    ###   1) it is in the curated KNOWN_ABSTRACT_NOUNS list,
    ###   2) otherwise, morphological test on the suffix (-tion, -ism, -ity...).
    lemma = lemma.lower()
    if lemma in KNOWN_ABSTRACT_NOUNS:
        return True
    return lemma.endswith(ABSTRACT_SUFFIXES)


### ---------------------
### 3. SPACY + MATCHER
### ---------------------
logging.info("Chargement du modèle spaCy (en_core_web_sm)...")
nlp = spacy.load("en_core_web_sm", disable=["ner"])

matcher = Matcher(nlp.vocab)
### Pattern A (nominal): "the cancer/disease/virus/plague/epidemic/sickness/
### illness/infection OF (det/adj)* NOUN+"
pattern_nominal = [
    {"LEMMA": {"IN": ["cancer", "disease", "virus", "plague", "epidemic",
                       "sickness", "illness", "infection"]}},
    {"LOWER": "of"},
    {"POS": {"IN": ["DET", "ADJ"]}, "OP": "*"},
    {"POS": "NOUN", "OP": "+"},
]
### Pattern B (verbal): "infected/plagued/sickened/poisoned/afflicted
### BY/WITH (det/adj)* NOUN+"
pattern_verbal = [
    {"LEMMA": {"IN": ["infect", "plague", "sicken", "poison", "afflict"]}},
    {"LOWER": {"IN": ["by", "with"]}},
    {"POS": {"IN": ["DET", "ADJ"]}, "OP": "*"},
    {"POS": "NOUN", "OP": "+"},
]
matcher.add("DISEASE_METAPHOR_TARGET", [pattern_nominal, pattern_verbal])


### ---------------------
### 4. REGRESSION TESTS
### ---------------------
def run_regression_tests():
    ### Non-regression test set. ANY change to the lexicons or the heuristic must
    ### pass on THESE sentences before touching the real corpus. Add here every
    ### sentence that caused trouble at some point: best guarantee that the
    ### classification stays stable.
    logging.info("Lancement des tests de régression...")
    test_cases = [
        ### Literal cases (real clinical context)
        ("The patient was admitted to the hospital.", "literal"),
        ("The doctor prescribed new medication for the illness.", "literal"),
        ("The nurse monitored the patient's vital signs in the ward.", "literal"),
        ("Surgery was scheduled for early Monday morning.", "literal"),
        ("The clinic provides free vaccines to children every spring.", "literal"),
        ("The physician reviewed the diagnosis before writing a prescription.", "literal"),
        ("Doctors and nurses worked around the clock in the hospital.", "literal"),
        ("The patient's symptoms improved after the treatment.", "literal"),
        ("The hospital quarantined patients exposed to the virus.", "literal"),
        ("The vaccine was administered to hundreds of patients this week.", "literal"),

        ### Metaphorical cases, nominal pattern "the X of ___"
        ("This is the cancer of corruption eating away at our institutions.", "metaphorical"),
        ("We must confront the disease of racism in our society.", "metaphorical"),
        ("The virus of extremism continues to spread across the country.", "metaphorical"),
        ("The plague of ignorance still holds too many communities back.", "metaphorical"),
        ("An epidemic of violence has gripped our cities for too long.", "metaphorical"),
        ("The sickness of greed has taken hold of Washington.", "metaphorical"),
        ("Officials warn that the infection of misinformation is spreading online.", "metaphorical"),

        ### Metaphorical cases, verbal pattern "infected/plagued/... by/with ___"
        ("Our politics have been infected by division and mistrust.", "metaphorical"),
        ("The nation remains plagued by inequality.", "metaphorical"),
        ("Communities have been poisoned by prejudice for generations.", "metaphorical"),
        ("This institution has been sickened by corruption for decades.", "metaphorical"),
        ("Our discourse has been afflicted by partisanship.", "metaphorical"),

        ### Metaphorical cases through markers only (no dynamic pattern)
        ("Racism and hatred continue to divide our nation.", "metaphorical"),
        ("Terrorism and radicalization threaten our shared future.", "metaphorical"),

        ### Ambiguous cases
        ("It is a sickness.", "ambiguous"),
        ("The illness continued for years.", "ambiguous"),
        ("The virus spread quickly last winter.", "ambiguous"),
        ("They discussed the situation yesterday.", "ambiguous"),
        ("It was a difficult moment for everyone.", "ambiguous"),
        ("The meeting ended without resolution.", "ambiguous"),
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


### ---------------------
### 5. MAIN ANALYSIS FUNCTION
### ---------------------
def analyze_sentence(text, corpus_name, kwic_word=None, kwic_char_pos=None, reference=None):
    ### kwic_word / kwic_char_pos: with a Sketch Engine KWIC export, the real node
    ### word (and ideally its exact character offset in `text`) is known. Left/right
    ### traceability is then measured from THAT node instead of the artificial middle
    ### of the sentence -> the distances actually mean something.
    ### reference: source-document metadata (Sketch Engine Reference column), copied
    ### as-is into the result so every hit can be traced back to its speech.
    try:
        doc = nlp(text)

        score_lit = 0
        score_meta = 0
        traceability = []
        dynamic_targets = []

        ### Pick the pivot (node) token:
        ###  1) exact character offset if given (Sketch Engine xlsx),
        ###  2) otherwise, look for kwic_word in the text,
        ###  3) otherwise (txt without a known node), middle of the sentence.
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

        ### Dynamic extraction (the cancer/disease/virus/... of ___ /
        ### infected/plagued/sickened/poisoned/afflicted by/with ___)
        ### -> only counts if the target noun is abstract.
        matches = matcher(doc)
        for match_id, start, end in matches:
            span = doc[start:end]
            target_noun = span[-1].lemma_.lower()
            target_side = "left" if span[-1].i < middle_index else "right"
            target_distance = abs(span[-1].i - middle_index)

            if is_abstract_noun(target_noun):
                score_meta += 2  ### heavier weight: explicit syntactic structure
                dynamic_targets.append(target_noun)
                traceability.append({
                    "marker": f"dynamic:{target_noun}",
                    "type": "metaphorical",
                    "side": target_side,
                    "distance": target_distance
                })

        ### Normalised confidence score, always within ]-1, 1[ (+1 in the denominator).
        ### > 0 metaphorical, < 0 literal, exactly 0 ambiguous (includes "no marker at all").
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


### ---------------------
### 6. CORPUS LOADING (Sketch Engine exports: .txt or .xlsx)
### ---------------------
def _safe_str(value):
    ### Clean conversion of a cell value (NaN, float, None...) to a stripped str.
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def extract_corpus_name_from_reference(reference):
    ### Speaker/corpus name from the Sketch Engine Reference column,
    ### e.g. "doc#0,Trump/2016/T - 2016-07-21 - ..." -> "Trump".
    ### Only used when no explicit corpus_name is given (see load_corpus_from_kwic_excel).
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
    ### Rename the columns to the canonical Reference/Left/Kwic/Right,
    ### whatever the case or stray spaces in the export.
    canonical = {"reference": "Reference", "left": "Left", "kwic": "Kwic", "right": "Right"}
    rename_map = {col: canonical[str(col).strip().lower()]
                  for col in df.columns if str(col).strip().lower() in canonical}
    return df.rename(columns=rename_map)


def load_corpus_from_file(filepath, corpus_name=None, encoding="utf-8"):
    ### Loads a concordance export in plain text (.txt). Two usual formats, line by
    ### line; a malformed line is logged and skipped, the rest keeps going:
    ###   - "plain sentence": one sentence per line,
    ###   - tab-separated KWIC: "left context \t node \t right context", the 3
    ###     columns glued back into one sentence.
    ###     NB: here the exact node index is lost (unlike .xlsx) -> left/right
    ###     traceability falls back on the middle of the sentence.
    ### Returns a list of dicts {"corpus", "text", "kwic", "reference"}
    ### (kwic/reference = None for this format).
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
    ### Loads a Sketch Engine KWIC export (.xlsx) with the columns
    ### "Reference" / "Left" / "Kwic" / "Right" (same layout as diseasemeta-test.xlsx).
    ###   - Keeps the node word (Kwic) and its exact character offset in the rebuilt
    ###     text (Left + Kwic + Right), so analyze_sentence() measures left/right
    ###     from the REAL node, not from the middle of the sentence.
    ###   - corpus_name given -> used for every row. Otherwise the corpus name is
    ###     read from Reference row by row (useful when one file mixes several
    ###     speakers/years).
    ###   - Each malformed row is logged and skipped without stopping the load.
    ### Returns a list of dicts {"corpus", "text", "kwic", "kwic_char_pos", "reference"}.
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

            ### Rebuild the text + exact character offset of the node
            parts = []
            if left:
                parts.append(left)
            kwic_char_pos = sum(len(p) + 1 for p in parts)  ### +1 = joining space
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
    ### Generic dispatcher: picks the loader from the extension
    ### (.xlsx/.xls -> Sketch Engine KWIC export, anything else -> .txt).
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".xlsx", ".xls"):
        return load_corpus_from_kwic_excel(filepath, corpus_name=corpus_name)
    return load_corpus_from_file(filepath, corpus_name=corpus_name)


### ---------------------
### 7. PROCESSING + EXPORTS
### ---------------------
def process_corpus(records, corpus_name):
    ### records: list of dicts (see load_corpus*) OR plain list of sentences (str),
    ### so the function also works for quick ad hoc tests.
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
            ### Extra safety net: one corrupted hit must never stop the processing
            ### of the whole corpus.
            logging.error(f"Échec inattendu sur l'occurrence #{idx} du corpus {corpus_name}, ignorée -> {str(e)}")
            continue

    return results


def generate_exports(df, sample_size=30, output_path=None):
    ### Writes the 4-sheet Excel workbook: All_Data, Summary,
    ### Inter_Annotator_Task (to annotate by hand), Metaphor_Targets_Freq.
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_path = output_path or f"NLP_Results_{timestamp}.xlsx"

    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        ### Sheet 1: raw data (one row per hit)
        df.to_excel(writer, sheet_name='All_Data', index=False)

        ### Sheet 2: summary (literal / metaphorical / ambiguous), overall first, then
        ### per corpus (needed as soon as one file mixes several presidents).
        logging.info("Génération de la synthèse (Summary)...")
        CATEGORIES = ["literal", "metaphorical", "ambiguous"]

        if df.empty:
            pd.DataFrame({"Message": ["Aucune donnée à synthétiser"]}).to_excel(
                writer, sheet_name='Summary', index=False
            )
        else:
            ### Overall summary
            overall_counts = df['category'].value_counts().reindex(CATEGORIES, fill_value=0)
            overall_df = pd.DataFrame({
                "category": list(CATEGORIES) + ["TOTAL"],
                "count": list(overall_counts.values) + [int(overall_counts.sum())],
            })
            overall_df["% of total"] = (
                overall_df["count"] / overall_df["count"].iloc[-1] * 100
            ).round(1)

            ### Summary per corpus (one president = one row)
            per_corpus = pd.crosstab(df['corpus'], df['category'])
            for cat in CATEGORIES:
                if cat not in per_corpus.columns:
                    per_corpus[cat] = 0
            per_corpus = per_corpus[CATEGORIES]
            per_corpus["total"] = per_corpus.sum(axis=1)
            per_corpus.loc["TOTAL"] = per_corpus.sum(axis=0)
            per_corpus["% metaphorical"] = (
                per_corpus["metaphorical"] / per_corpus["total"] * 100
            ).round(1)
            per_corpus = per_corpus.reset_index().rename(columns={"corpus": "corpus"})

            overall_df.to_excel(writer, sheet_name='Summary', index=False, startrow=1, startcol=0)
            writer.sheets['Summary']['A1'] = "Synthèse globale (tous corpus confondus)"

            start_row_per_corpus = len(overall_df) + 4
            per_corpus.to_excel(writer, sheet_name='Summary', index=False,
                                 startrow=start_row_per_corpus, startcol=0)
            writer.sheets['Summary'][f'A{start_row_per_corpus}'] = "Synthèse par corpus / président"

        ### Sheet 3: stratified sample for manual annotation (sample_size rows max per
        ### category, fixed random_state so the sample can be regenerated identically).
        logging.info("Génération de l'échantillon stratifié...")
        stratified_parts = []
        for cat, group in df.groupby('category'):
            n = min(len(group), sample_size)
            stratified_parts.append(group.sample(n=n, random_state=42))
        stratified_sample = pd.concat(stratified_parts, ignore_index=True) if stratified_parts else df.iloc[0:0].copy()
        stratified_sample.insert(0, 'Manual_Annotation', '')
        stratified_sample.to_excel(writer, sheet_name='Inter_Annotator_Task', index=False)

        ### Sheet 4: frequency of the metaphor targets per corpus
        logging.info("Génération du tableau croisé des cibles...")
        df_targets = df[df['dynamic_targets'] != ""]
        if not df_targets.empty:
            df_exploded = df_targets.assign(
                dynamic_targets=df_targets['dynamic_targets'].str.split(', ')
            ).explode('dynamic_targets').reset_index(drop=True)
            ### reset_index(drop=True) is mandatory: as soon as a hit has SEVERAL dynamic
            ### targets (e.g. "poverty, terror"), .explode() duplicates the original index,
            ### and pd.crosstab(..., margins=True) then fails with "cannot reindex on an
            ### axis with duplicate labels".
            freq_table = pd.crosstab(df_exploded['dynamic_targets'], df_exploded['corpus'], margins=True)
            freq_table.to_excel(writer, sheet_name='Metaphor_Targets_Freq')
        else:
            pd.DataFrame({"Message": ["Aucune cible dynamique trouvée"]}).to_excel(
                writer, sheet_name='Metaphor_Targets_Freq'
            )

    logging.info(f"Export Excel terminé avec succès : {excel_path}")
    return excel_path


### ---------------------
### 8. INTER-ANNOTATOR RELIABILITY (precision / recall / agreement)
### ---------------------
def _confusion_counts(y_true, y_pred, labels):
    ### Confusion matrix as a dict {(true, pred): n}.
    counts = {(t, p): 0 for t in labels for p in labels}
    for t, p in zip(y_true, y_pred):
        if t in labels and p in labels:
            counts[(t, p)] += 1
    return counts


def _cohen_kappa(counts, labels, n):
    ### Cohen's kappa computed by hand from the confusion matrix.
    po = sum(counts[(l, l)] for l in labels) / n

    row_totals = {l: sum(counts[(l, p)] for p in labels) for l in labels}   ### ground truth
    col_totals = {l: sum(counts[(t, l)] for t in labels) for l in labels}   ### script prediction

    pe = sum((row_totals[l] / n) * (col_totals[l] / n) for l in labels)

    if pe == 1:
        return 1.0
    return (po - pe) / (1 - pe)


def evaluate_reliability(annotated_excel_path, sheet_name="Inter_Annotator_Task", report_excel_path=None):
    # Call this AFTER filling the 'Manual_Annotation' column by hand in the Inter_Annotator_Task sheet of the workbook written by generate_exports().
    # Compares:
    #   - 'category'          -> automatic prediction of the script
    #   - 'Manual_Annotation' -> ground truth (my manual annotation)
    # Computes overall accuracy, precision/recall/F1 per category and Cohen's
    # kappa (agreement beyond chance). Adds a 'Reliability_Report' sheet to the workbook (or to report_excel_path if given) 
    # and returns a dict with every metric, ready for the methodology chapter.
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
        fp = sum(counts[(t, l)] for t in labels if t != l)   ### predicted l, truth != l
        fn = sum(counts[(l, p)] for p in labels if p != l)   ### truth l, predicted != l

        precision = tp / (tp + fp) if (tp + fp) > 0 else float('nan')
        recall = tp / (tp + fn) if (tp + fn) > 0 else float('nan')
        if precision + recall > 0 and not (np.isnan(precision) or np.isnan(recall)):
            f1 = 2 * precision * recall / (precision + recall)
        else:
            f1 = float('nan')

        support = sum(counts[(l, p)] for p in labels)  ### real number of hits of this class (ground truth)
        per_class[l] = {"precision": precision, "recall": recall, "f1": f1, "support": support}

    kappa = _cohen_kappa(counts, labels, n)

    logging.info(f"Fiabilité calculée sur {n} lignes annotées : accuracy={accuracy:.3f}, kappa de Cohen={kappa:.3f}")

    ### Tables for the export
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


### ---------------------
### 9. RUN
### ---------------------
def load_all_corpora(corpus_files):
    ### corpus_files: dict {corpus_name: file_path}. The file can be a .txt (one
    ### sentence per line or tab-separated KWIC) OR an .xlsx (Sketch Engine KWIC
    ### export, Reference/Left/Kwic/Right); format picked from the extension
    ### (see load_corpus()). The dict key is applied to EVERY row of the file.
    ### Returns a dict {corpus_name: [records]}. A missing or empty file is logged
    ### as a warning and skipped instead of crashing the whole script.
    ### If a single .xlsx mixes several speakers and the corpus should be detected
    ### row by row from Reference, call load_corpus_from_kwic_excel(path,
    ### corpus_name=None) directly instead of using this dict.
    corpora = {}
    for name, path in corpus_files.items():
        records = load_corpus(path, corpus_name=name)
        if records:
            corpora[name] = records
        else:
            logging.warning(f"Corpus '{name}' vide ou illisible ({path}) — ignoré.")
    return corpora


def load_single_combined_file(filepath):
    ### Loads ONE Sketch Engine KWIC export (.xlsx) mixing the hits of several
    ### presidents/speakers in the same file.
    ### The corpus name is NOT forced: it is detected row by row from 'Reference'
    ### (see extract_corpus_name_from_reference), so two neighbouring rows can
    ### belong to different corpora.
    ### Returns {corpus_name: [records]}, exactly like load_all_corpora(), so the
    ### rest of the pipeline (process_corpus, generate_exports...) does not change.
    records = load_corpus_from_kwic_excel(filepath, corpus_name=None)
    corpora = {}
    for record in records:
        corpora.setdefault(record["corpus"], []).append(record)

    if not corpora:
        logging.warning(f"Aucune occurrence exploitable trouvée dans {filepath}.")
        return corpora

    for name, recs in corpora.items():
        logging.info(f"Corpus '{name}' détecté automatiquement dans {filepath} : {len(recs)} occurrences.")
    return corpora


if __name__ == "__main__":
    ### 1. Safety tests first: stop here if the classifier drifted
    run_regression_tests()

    ### 2. Load the corpora. Two modes:
    ###    a) SINGLE_CORPUS_FILE: ONE .xlsx mixing the hits of the 3 presidents;
    ###       the corpus of each row is detected from 'Reference'
    ###       (e.g. "doc#0,Trump/2016/..." -> "Trump"). Preferred mode when the
    ###       Sketch Engine export already combines the three corpora.
    ###    b) CORPUS_FILES: one .xlsx (or .txt) per president, corpus name forced
    ###       by the dict key -> only used if SINGLE_CORPUS_FILE is not on disk.
    ###    -> Neither found: falls back on demo sentences so the script still runs.
    SINGLE_CORPUS_FILE = "KWIC-disease-ALL.xlsx"

    CORPUS_FILES = {
        "Bush": "KWIC-disease-BUSH.xlsx",
        "Obama": "KWIC-disease-OBAMA.xlsx",
        "Trump": "KWIC-disease-TRUMP.xlsx",
    }

    if os.path.exists(SINGLE_CORPUS_FILE):
        logging.info(f"Fichier combiné détecté : {SINGLE_CORPUS_FILE} (chargement en un seul passage).")
        corpora = load_single_combined_file(SINGLE_CORPUS_FILE)
    else:
        corpora = load_all_corpora(CORPUS_FILES)

    if not corpora:
        logging.warning("Aucun fichier de corpus trouvé sur disque : utilisation des données de démonstration.")
        corpora = {
            "Bush": [
                "We must confront the disease of racism together.",
                "The patient was admitted to the hospital last night.",
                "This is a virus of extremism that threatens us all.",
            ],
            "Obama": [
                "Our politics have been infected by division and mistrust.",
                "The doctor prescribed new medication for the patient.",
                "The cancer of corruption must be cut out of government.",
            ],
            "Trump": [
                "This nation has been plagued by inequality for too long.",
                "Our great hospitals are ready with the vaccine.",
                "It is a sickness of crime spreading through our cities.",
            ],
        }

    ### 3. Processing
    all_results = []
    for corpus_name, sentences in corpora.items():
        all_results.extend(process_corpus(sentences, corpus_name))

    ### 4. Export (20 rows per category in the annotation sample)
    df_results = pd.DataFrame(all_results)
    excel_path = generate_exports(df_results, sample_size=20)

    logging.info("Processus complet terminé.")
    logging.info(
        f"ÉTAPE SUIVANTE : ouvre '{excel_path}', remplis la colonne 'Manual_Annotation' "
        "dans l'onglet Inter_Annotator_Task, puis appelle "
        f"evaluate_reliability('{excel_path}') pour obtenir accuracy / precision / recall / kappa."
    )
