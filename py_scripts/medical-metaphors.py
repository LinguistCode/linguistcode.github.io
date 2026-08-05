import pandas as pd
import re

df = pd.read_excel('./data_src/KWIC-Metaphores_maladie.xlsx')

# Literal indicators in context
LITERAL_PATTERNS = [
    r'\b(diagnosed|diagnosis|doctor|physician|hospital|clinic|treatment|therapy|medicine|patient|medical|health care|healthcare)\b',
    r'\b(rare disease|pompe|prescription|overdose|alzheimer|autism|cancer survivor|cancer patient|cancer treatment|chemotherapy)\b',
    r'\b(disease day|awareness|ribbon|fundrais|research fund)\b',
    r'\b(insurance|medicaid|medicare|affordable care|health plan|health bill|repeal|replace)\b',
    r'\b(bacteria|pathogen|outbreak|contagious|transmit|spread of)\b',
    r'\b(lung|heart|brain|blood|organ|tumor|cyst|lesion|clinical)\b',
    r'\b(veterans|vets|VA|wait\s+on\s+line|wait\s+in\s+line)\b',
    r'\b(getting sicker|fell sick|sick leave|sick day|sick note|sick bed)\b',
    r'\b(infection rate|infectious disease|disease control|CDC|NIH|FDA)\b',
    r'\b(food safety|water supply|drinking water)\b',
    r'\b(sickle cell)\b',
]

# Metaphorical indicators in context
METAPHOR_PATTERNS = [
    r'\b(terrorism|terrorist|terror|ISIS|radical Islam|jihad|Al.?Qaeda|extremis)\b',
    r'\b(crime|criminal|gang|cartel|MS-13|drug dealer|traffick)\b',
    r'\b(corrupt|corruption|swamp|establishment|media|fake news|mainstream)\b',
    r'\b(our planet|our world|humanity|society|nation|country|civilization|the earth|the world)\b',
    r'\b(eradicat|eliminat|wipe out|stamp out|defeat|destroy|kill)\b',
    r'\b(spread(ing)? of|plaguing|plagues our|plague on|plague of)\b',
    r'\b(political|politics|politicians|congress|democrat|republican|left|liberal|socialist)\b',
    r'\b(immigration|immigrants|illegal|alien|border|invasion)\b',
    r'\b(moral|soul|spirit|values|decadence|decay|rot|filth of)\b',
    r'\b(parasite|leech|vermin|rodent|infestation)\b',
    r'\b(media|press|journalism|fake|hoax|witch hunt)\b',
    r'\b(economy|economic|financial|market|trade|deal)\b',
    r'\bsick\s+(and\s+)?(twisted|perverted|disgusting|demented|pathetic|joke|system|culture)\b',
    r'\b(sicko|sickos|filthy|filth)\b',
    r'\b(human rights|social justice|poverty|inequality|injustice)\b',
    r'\b(infect(ing|ed|s)?|infest(ing|ed|s)?)\b',
    r'\b(cancerous|cancer of|cancer in|cancer on)\b',
]

ALMOST_ALWAYS_METAPHOR_KWIC = {
    'sicko', 'sickos', 'filthy', 'filth', 'plagued', 'plagues', 'plaguing',
    'plague', 'Plague', 'parasites', 'parasite', 'cancerous', 'infests', 'sickening',
}

OFTEN_LITERAL_KWIC = {
    'sickle', 'sick-day', 'disease-free', 'cancer-free', 'disease-causing', 'cancer-causing',
}

def classify_row(row):
    kwic = str(row['Kwic']).strip()
    left = str(row['Left']).strip().lower() if pd.notna(row['Left']) else ''
    right = str(row['Right']).strip().lower() if pd.notna(row['Right']) else ''
    context = left + ' ' + right

    if kwic.lower() in {s.lower() for s in ALMOST_ALWAYS_METAPHOR_KWIC}:
        return 'metaphorical', 'KWIC term is inherently derogatory/figurative'
    if kwic.lower() in {s.lower() for s in OFTEN_LITERAL_KWIC}:
        return 'literal', 'KWIC term is a medical compound'

    literal_score, metaphor_score = 0, 0
    lit_matches, met_matches = [], []

    for pat in LITERAL_PATTERNS:
        m = re.search(pat, context, re.IGNORECASE)
        if m:
            literal_score += 1
            lit_matches.append(m.group())

    for pat in METAPHOR_PATTERNS:
        m = re.search(pat, context, re.IGNORECASE)
        if m:
            metaphor_score += 1
            met_matches.append(m.group())

    if re.search(r'rare disease day', context, re.IGNORECASE):
        return 'literal', 'Rare Disease Day (event name)'
    if re.search(r'\b(disease|cancer|infection)-\w+\b', kwic, re.IGNORECASE):
        return 'literal', 'Medical compound term'
    if kwic.lower() in ('sicker',) and re.search(r'\b(wait|line|veteran|VA)\b', context, re.IGNORECASE):
        return 'literal', 'Literal medical deterioration (VA context)'

    if metaphor_score > literal_score:
        return 'metaphorical', f"Metaphorical context: {', '.join(met_matches[:3])}"
    elif literal_score > metaphor_score:
        return 'literal', f"Medical/health context: {', '.join(lit_matches[:3])}"
    else:
        # Tie-breaking by KWIC
        if kwic.lower() in ('cancer', 'cancers', "cancer's"):
            if re.search(r'\b(beat|fought|survivor|patient|diagnos|treat|chemo|stage|tumor)\b', context, re.IGNORECASE):
                return 'literal', 'Cancer as medical condition'

            return 'unclear', 'Cancer: No strong context, manual review needed' 
            
        if kwic.lower() in ('sick', 'Sick'):
            if re.search(r'\b(patient|symptom|ill|hospital|doctor|feel|felt|getting|came down)\b', context, re.IGNORECASE):
                return 'literal', 'Sick in medical/physical sense'

            return 'unclear', 'Sick: No strong context, manual review needed'
            
        if kwic.lower() in ('disease', 'Disease', 'diseases', 'Diseases'):
            if re.search(r'\b(health|treatment|cure|drug|patient|diagnos|medical)\b', context, re.IGNORECASE):
                return 'literal', 'Disease in medical context'

            return 'unclear', 'Disease: No strong context, manual review needed'
            
        return 'unclear', 'No signals detected; manual review needed'

labels, reasons = [], []
for _, row in df.iterrows():
    label, reason = classify_row(row)
    labels.append(label)
    reasons.append(reason)

df['classification'] = labels
df['reason'] = reasons
df.to_csv('classified_all.csv', index=False)