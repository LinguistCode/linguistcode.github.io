/**
 * medical-metaphors.js
 * -----------------------------------------------------------------
 * Portage JS de medical-metaphors.py.
 *
 * Contrairement aux autres modules, celui-ci accepte un fichier .xlsx
 * fourni par l'utilisateur (lu entièrement côté client via SheetJS —
 * aucun envoi réseau, rien ne quitte le navigateur). La classification
 * reproduit fidèlement les règles Python (mêmes regex, même ordre de
 * priorité), puis propose le résultat en téléchargement CSV.
 *
 * Colonnes attendues dans le fichier (insensible à la casse) :
 *   Kwic, Left, Right   — export KWIC Sketch Engine standard.
 */

(function () {
    // ---------- Règles portées telles quelles depuis medical-metaphors.py ----------

    const LITERAL_PATTERNS = [
        /\b(diagnosed|diagnosis|doctor|physician|hospital|clinic|treatment|therapy|medicine|patient|medical|health care|healthcare)\b/i,
        /\b(rare disease|pompe|prescription|overdose|alzheimer|autism|cancer survivor|cancer patient|cancer treatment|chemotherapy)\b/i,
        /\b(disease day|awareness|ribbon|fundrais|research fund)\b/i,
        /\b(insurance|medicaid|medicare|affordable care|health plan|health bill|repeal|replace)\b/i,
        /\b(bacteria|pathogen|outbreak|contagious|transmit|spread of)\b/i,
        /\b(lung|heart|brain|blood|organ|tumor|cyst|lesion|clinical)\b/i,
        /\b(veterans|vets|VA|wait\s+on\s+line|wait\s+in\s+line)\b/i,
        /\b(getting sicker|fell sick|sick leave|sick day|sick note|sick bed)\b/i,
        /\b(infection rate|infectious disease|disease control|CDC|NIH|FDA)\b/i,
        /\b(food safety|water supply|drinking water)\b/i,
        /\b(sickle cell)\b/i,
    ];

    const METAPHOR_PATTERNS = [
        /\b(terrorism|terrorist|terror|ISIS|radical Islam|jihad|Al.?Qaeda|extremis)\b/i,
        /\b(crime|criminal|gang|cartel|MS-13|drug dealer|traffick)\b/i,
        /\b(corrupt|corruption|swamp|establishment|media|fake news|mainstream)\b/i,
        /\b(our planet|our world|humanity|society|nation|country|civilization|the earth|the world)\b/i,
        /\b(eradicat|eliminat|wipe out|stamp out|defeat|destroy|kill)\b/i,
        /\b(spread(ing)? of|plaguing|plagues our|plague on|plague of)\b/i,
        /\b(political|politics|politicians|congress|democrat|republican|left|liberal|socialist)\b/i,
        /\b(immigration|immigrants|illegal|alien|border|invasion)\b/i,
        /\b(moral|soul|spirit|values|decadence|decay|rot|filth of)\b/i,
        /\b(parasite|leech|vermin|rodent|infestation)\b/i,
        /\b(media|press|journalism|fake|hoax|witch hunt)\b/i,
        /\b(economy|economic|financial|market|trade|deal)\b/i,
        /\bsick\s+(and\s+)?(twisted|perverted|disgusting|demented|pathetic|joke|system|culture)\b/i,
        /\b(sicko|sickos|filthy|filth)\b/i,
        /\b(human rights|social justice|poverty|inequality|injustice)\b/i,
        /\b(infect(ing|ed|s)?|infest(ing|ed|s)?)\b/i,
        /\b(cancerous|cancer of|cancer in|cancer on)\b/i,
    ];

    const ALMOST_ALWAYS_METAPHOR_KWIC = new Set(
        ['sicko', 'sickos', 'filthy', 'filth', 'plagued', 'plagues', 'plaguing',
            'plague', 'Plague', 'parasites', 'parasite', 'cancerous', 'infests', 'sickening']
            .map(s => s.toLowerCase())
    );

    const OFTEN_LITERAL_KWIC = new Set(
        ['sickle', 'sick-day', 'disease-free', 'cancer-free', 'disease-causing', 'cancer-causing']
            .map(s => s.toLowerCase())
    );

    function safeStr(value) {
        if (value === null || value === undefined) return '';
        return String(value).trim();
    }

    // Reproduit classify_row() de medical-metaphors.py, ligne par ligne.
    function classifyRow(row) {
        const kwic = safeStr(row['Kwic']);
        const left = row['Left'] !== null && row['Left'] !== undefined ? safeStr(row['Left']).toLowerCase() : '';
        const right = row['Right'] !== null && row['Right'] !== undefined ? safeStr(row['Right']).toLowerCase() : '';
        const context = left + ' ' + right;
        const kwicLower = kwic.toLowerCase();

        if (ALMOST_ALWAYS_METAPHOR_KWIC.has(kwicLower)) {
            return ['metaphorical', 'KWIC term is inherently derogatory/figurative'];
        }
        if (OFTEN_LITERAL_KWIC.has(kwicLower)) {
            return ['literal', 'KWIC term is a medical compound'];
        }

        let literalScore = 0, metaphorScore = 0;
        const litMatches = [], metMatches = [];

        for (const pat of LITERAL_PATTERNS) {
            const m = context.match(pat);
            if (m) {
                literalScore += 1;
                litMatches.push(m[0]);
            }
        }

        for (const pat of METAPHOR_PATTERNS) {
            const m = context.match(pat);
            if (m) {
                metaphorScore += 1;
                metMatches.push(m[0]);
            }
        }

        if (/rare disease day/i.test(context)) {
            return ['literal', 'Rare Disease Day (event name)'];
        }
        if (/\b(disease|cancer|infection)-\w+\b/i.test(kwic)) {
            return ['literal', 'Medical compound term'];
        }
        if (kwicLower === 'sicker' && /\b(wait|line|veteran|VA)\b/i.test(context)) {
            return ['literal', 'Literal medical deterioration (VA context)'];
        }

        if (metaphorScore > literalScore) {
            return ['metaphorical', `Metaphorical context: ${metMatches.slice(0, 3).join(', ')}`];
        } else if (literalScore > metaphorScore) {
            return ['literal', `Medical/health context: ${litMatches.slice(0, 3).join(', ')}`];
        } else {
            // Départage par KWIC (tie-breaking)
            if (['cancer', 'cancers', "cancer's"].includes(kwicLower)) {
                if (/\b(beat|fought|survivor|patient|diagnos|treat|chemo|stage|tumor)\b/i.test(context)) {
                    return ['literal', 'Cancer as medical condition'];
                }
                return ['unclear', 'Cancer: No strong context, manual review needed'];
            }

            if (kwicLower === 'sick') {
                if (/\b(patient|symptom|ill|hospital|doctor|feel|felt|getting|came down)\b/i.test(context)) {
                    return ['literal', 'Sick in medical/physical sense'];
                }
                return ['unclear', 'Sick: No strong context, manual review needed'];
            }

            if (['disease', 'diseases'].includes(kwicLower)) {
                if (/\b(health|treatment|cure|drug|patient|diagnos|medical)\b/i.test(context)) {
                    return ['literal', 'Disease in medical context'];
                }
                return ['unclear', 'Disease: No strong context, manual review needed'];
            }

            return ['unclear', 'No signals detected; manual review needed'];
        }
    }

    // ---------- Lecture du fichier xlsx côté client (SheetJS) ----------

    function loadSheetJs() {
        if (window.XLSX) return Promise.resolve();
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
            script.onload = () => resolve();
            script.onerror = () => reject(new Error("Impossible de charger la librairie de lecture xlsx (SheetJS)."));
            document.head.appendChild(script);
        });
    }

    function normalizeColumns(rows) {
        // Rend la lecture des colonnes insensible à la casse/espaces, comme
        // pourrait le faire un utilisateur import son propre export KWIC.
        return rows.map(row => {
            const normalized = {};
            for (const key of Object.keys(row)) {
                const canon = key.trim().toLowerCase();
                if (canon === 'kwic') normalized['Kwic'] = row[key];
                else if (canon === 'left') normalized['Left'] = row[key];
                else if (canon === 'right') normalized['Right'] = row[key];
                else normalized[key] = row[key];
            }
            return normalized;
        });
    }

    function readWorkbook(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const data = new Uint8Array(e.target.result);
                    const workbook = window.XLSX.read(data, { type: 'array' });
                    const firstSheetName = workbook.SheetNames[0];
                    const sheet = workbook.Sheets[firstSheetName];
                    const rows = window.XLSX.utils.sheet_to_json(sheet, { defval: null });
                    resolve({ rows: normalizeColumns(rows), sheetName: firstSheetName });
                } catch (err) {
                    reject(err);
                }
            };
            reader.onerror = () => reject(new Error("Échec de la lecture du fichier."));
            reader.readAsArrayBuffer(file);
        });
    }

    // ---------- Génération et téléchargement du CSV résultat ----------

    function toCsv(rows) {
        if (rows.length === 0) return '';
        const columns = Object.keys(rows[0]);

        function escapeCsvField(value) {
            const str = value === null || value === undefined ? '' : String(value);
            if (/[",\n]/.test(str)) {
                return `"${str.replace(/"/g, '""')}"`;
            }
            return str;
        }

        const header = columns.map(escapeCsvField).join(',');
        const lines = rows.map(row => columns.map(c => escapeCsvField(row[c])).join(','));
        return [header, ...lines].join('\n');
    }

    function triggerCsvDownload(csvContent, filename) {
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    // ---------- UI du module ----------

    let selectedFile = null;
    let lastResultRows = null;

    function renderForm() {
        return `
        <div class="input-group">
            <label class="text-xs mb-1 block opacity-80">> Fichier KWIC (.xlsx) — colonnes attendues : Kwic, Left, Right</label>
            <input type="file" id="mm-file" accept=".xlsx,.xls" class="terminal-input">
        </div>
        <div id="mm-file-status" class="text-xs opacity-70 mb-4"></div>
        <button id="run-btn" class="terminal-btn w-full" disabled>EXECUTE --classify (choisissez un fichier)</button>
        <div id="mm-download-zone" class="mt-4"></div>`;
    }

    function onFormReady(formzone) {
        selectedFile = null;
        lastResultRows = null;

        const fileInput = formzone.querySelector('#mm-file');
        const status = formzone.querySelector('#mm-file-status');
        const runBtn = formzone.querySelector('#run-btn');
        const downloadZone = formzone.querySelector('#mm-download-zone');

        fileInput.addEventListener('change', () => {
            downloadZone.innerHTML = '';
            lastResultRows = null;

            const file = fileInput.files[0];
            if (!file) {
                selectedFile = null;
                status.textContent = '';
                runBtn.disabled = true;
                runBtn.textContent = 'EXECUTE --classify (choisissez un fichier)';
                return;
            }
            selectedFile = file;
            status.textContent = `Fichier sélectionné : ${file.name} (${(file.size / 1024).toFixed(1)} Ko) — traité localement, jamais envoyé sur un serveur.`;
            runBtn.disabled = false;
            runBtn.textContent = 'EXECUTE --classify';
        });

        runBtn.addEventListener('click', async () => {
            const scrollback = createScrollback(document.getElementById('terminal-scrollback'));
            runBtn.disabled = true;
            const originalLabel = runBtn.textContent;
            runBtn.textContent = 'EXECUTING...';
            downloadZone.innerHTML = '';

            try {
                await runClassification(selectedFile, scrollback, downloadZone);
            } finally {
                runBtn.disabled = false;
                runBtn.textContent = originalLabel;
            }
        });
    }

    async function runClassification(file, scrollback, downloadZone) {
        if (!file) {
            scrollback.print("[ERROR] Aucun fichier sélectionné.", "tl-error");
            return;
        }

        await scrollback.thinking("chargement de la librairie de lecture xlsx");
        try {
            await loadSheetJs();
        } catch (err) {
            scrollback.print(`[ERROR] ${err.message}`, "tl-error");
            return;
        }

        await scrollback.thinking(`lecture de ${file.name}`);
        let rows, sheetName;
        try {
            ({ rows, sheetName } = await readWorkbook(file));
        } catch (err) {
            scrollback.print(`[ERROR] Impossible de lire le fichier : ${err.message}`, "tl-error");
            return;
        }

        if (rows.length === 0) {
            scrollback.print("[ERROR] La feuille lue est vide.", "tl-error");
            return;
        }

        const hasKwic = Object.prototype.hasOwnProperty.call(rows[0], 'Kwic');
        if (!hasKwic) {
            scrollback.print(`[ERROR] Colonne "Kwic" introuvable dans la feuille "${sheetName}". Colonnes détectées : ${Object.keys(rows[0]).join(', ')}`, "tl-error");
            return;
        }

        await scrollback.printTyped(`> ${rows.length} lignes chargées depuis la feuille "${sheetName}"...`, "tl-info", 8);
        await scrollback.thinking("classification en cours");

        const counts = { metaphorical: 0, literal: 0, unclear: 0 };
        const resultRows = rows.map(row => {
            const [classification, reason] = classifyRow(row);
            counts[classification] = (counts[classification] || 0) + 1;
            return { ...row, classification, reason };
        });

        lastResultRows = resultRows;

        scrollback.print("", "");
        scrollback.print("[RÉSULTATS]", "tl-highlight");
        scrollback.print(`-> Total analysé      : ${rows.length} occurrences`, "tl-success");
        scrollback.print(`-> Métaphorique       : ${counts.metaphorical || 0}`, "tl-success");
        scrollback.print(`-> Littéral           : ${counts.literal || 0}`, "tl-success");
        scrollback.print(`-> Ambigu (unclear)   : ${counts.unclear || 0}`, "tl-warn");
        scrollback.print("", "");
        scrollback.print(">> Fichier CSV prêt au téléchargement ci-dessous.", "tl-info");

        const csv = toCsv(resultRows);
        const outFilename = file.name.replace(/\.(xlsx|xls)$/i, '') + '_classified.csv';

        downloadZone.innerHTML = `
            <button id="mm-download-btn" class="terminal-btn w-full" style="background-color:#1f6feb;">
                ↓ TÉLÉCHARGER ${outFilename}
            </button>`;
        downloadZone.querySelector('#mm-download-btn').addEventListener('click', () => {
            triggerCsvDownload(csv, outFilename);
        });
    }

    registerTerminalScript({
        id: "medical-metaphors",
        pill: "medical_metaphors.js",
        command: "./medical_metaphors.py --input <votre_fichier.xlsx>",
        ready: true,
        selfManagesRunButton: true, // gère son propre bouton (dépend de la sélection de fichier)
        intro: [
            { text: "Portage JS de medical-metaphors.py — classification littéral/métaphorique/ambigu.", cls: "tl-comment" },
            { text: "Déposez votre propre export KWIC (.xlsx, colonnes Kwic/Left/Right) : tout est traité localement dans votre navigateur, rien n'est envoyé sur un serveur.", cls: "tl-comment" }
        ],
        renderForm,
        onFormReady,
        async run(scrollback) {
            // no-op : le bouton EXECUTE réel est branché dans onFormReady()
        }
    });
})();
