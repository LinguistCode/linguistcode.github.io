/** --uber-anova.js--
 * -------------------------------------------------------------
 * chaque corpus (Bush / Obama / Trump) est découpé en blocs de N tokens, un index Über est calculé par bloc,
 * puis les trois distributions sont comparées par une ANOVA à un facteur (scipy.stats.f_oneway) et, 
 * si p < 0.05, par le test post-hoc de Tukey HSD (scipy.stats.tukey_hsd).
 * -------------------------------------------------------------
 */

(function () {
    const WORD = /[\p{L}\p{N}_]+/gu; // équivalent de \b\w+\b (Python, Unicode)
    const GROUPS = [
        { key: "bush", label: "Bush" },
        { key: "obama", label: "Obama" },
        { key: "trump", label: "Trump" }
    ];

    function calculateUberIndex(nTokens, nTypes) {
        if (nTokens <= 1) return 0;
        if (nTokens === nTypes) return 0;
        return (Math.log(nTokens) ** 2) / (Math.log(nTokens) - Math.log(nTypes));
    }

    // Lecture en flux : les blocs sont calculés au fil de l'eau, sans garder
    // tous les tokens en mémoire (le dernier bloc incomplet est ignoré).
    async function getUberScores(files, chunkSize, scrollback, label) {
        const ordered = TH.walkOrder(files.filter(f => /\.txt$/.test(f.name)));
        const scores = [];
        let count = 0;
        let chunkTypes = new Set();
        for (let i = 0; i < ordered.length; i++) {
            let text;
            try {
                text = await TH.readText(ordered[i], "ignore");
            } catch (e) {
                scrollback.print(`Erreur ignorée sur ${TH.relPath(ordered[i])} : ${e.message}`, "tl-warn");
                continue;
            }
            const tokens = text.toLowerCase().match(WORD) || [];
            for (const t of tokens) {
                chunkTypes.add(t);
                count++;
                if (count === chunkSize) {
                    scores.push(calculateUberIndex(count, chunkTypes.size));
                    count = 0;
                    chunkTypes = new Set();
                }
            }
            if (i % 50 === 49) await TH.yieldToBrowser();
        }
        return { scores, nFiles: ordered.length };
    }

    // scipy.stats.f_oneway
    function fOneway(groups) {
        const k = groups.length;
        const N = groups.reduce((s, g) => s + g.length, 0);
        const grand = groups.flat().reduce((s, v) => s + v, 0) / N;
        let ssb = 0, ssw = 0;
        for (const g of groups) {
            const m = TH.mean(g);
            ssb += g.length * (m - grand) ** 2;
            for (const v of g) ssw += (v - m) ** 2;
        }
        const dfb = k - 1, dfw = N - k;
        const F = (ssb / dfb) / (ssw / dfw);
        return { F, p: TH.fSf(F, dfb, dfw), dfw };
    }

    // scipy.stats.tukey_hsd (Tukey-Kramer si effectifs inégaux), IC 95 %
    function tukeyHsd(groups) {
        const k = groups.length;
        const N = groups.reduce((s, g) => s + g.length, 0);
        const df = N - k;
        const means = groups.map(TH.mean);
        const mse = groups.reduce((s, g) => s + (g.length - 1) * TH.variance(g, 1), 0) / df;
        const crit = TH.qtukey(0.95, k, df);
        const rows = [];
        for (let i = 0; i < k; i++) {
            for (let j = 0; j < k; j++) {
                if (i === j) continue;
                const diff = means[i] - means[j];
                const se = Math.sqrt((mse / 2) * (1 / groups[i].length + 1 / groups[j].length));
                const p = 1 - TH.ptukey(Math.abs(diff) / se, k, df);
                rows.push({ i, j, diff, p: Math.max(0, p), lo: diff - crit * se, hi: diff + crit * se });
            }
        }
        return rows;
    }

    function renderForm() {
        const inputs = GROUPS.map(g => `
            <div class="input-group">
                <label class="text-xs mb-1 block opacity-80">> Dossier ${g.label}</label>
                <input type="file" id="ua-${g.key}" class="terminal-input" webkitdirectory directory multiple>
            </div>`).join("");
        return `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-2">${inputs}</div>
        <div class="input-group">
            <label class="text-xs mb-1 block opacity-80">> Taille des blocs (tokens)</label>
            <input type="number" id="ua-chunk" class="terminal-input" value="10000" min="2">
        </div>
        <button id="run-btn" class="terminal-btn w-full">EXECUTE --uber-anova</button>`;
    }

    async function run(scrollback) {
        const chunkSize = parseInt(document.getElementById("ua-chunk").value, 10);
        const fileSets = GROUPS.map(g => Array.from(document.getElementById(`ua-${g.key}`).files || []));
        if (fileSets.some(fs => fs.length === 0)) {
            scrollback.print("[ERROR] Veuillez sélectionner les trois dossiers (Bush, Obama, Trump).", "tl-error");
            return;
        }
        if (!(chunkSize >= 2)) {
            scrollback.print("[ERROR] La taille des blocs doit être un entier ≥ 2.", "tl-error");
            return;
        }

        scrollback.print(`Génération des échantillons (${chunkSize} mots par bloc)...`, "tl-info");
        const scores = [];
        for (let g = 0; g < GROUPS.length; g++) {
            await scrollback.thinking(`découpage du corpus ${GROUPS[g].label}`, 300);
            const res = await getUberScores(fileSets[g], chunkSize, scrollback, GROUPS[g].label);
            scores.push(res.scores);
        }
        scrollback.print(`Blocs générés : Bush (${scores[0].length}), Obama (${scores[1].length}), Trump (${scores[2].length})`, "tl-info");
        scrollback.print("", "");

        if (scores.some(s => s.length < 2)) {
            scrollback.print("[ERROR] Chaque corpus doit fournir au moins 2 blocs complets : réduisez la taille des blocs ou ajoutez des fichiers.", "tl-error");
            return;
        }

        await scrollback.thinking("ANOVA à un facteur (scipy.stats.f_oneway)");
        const { F, p } = fOneway(scores);
        scrollback.print("=== RÉSULTATS ANOVA ===", "tl-highlight");
        scrollback.print(`Statistique F : ${TH.pyFixed(F, 4)}`, "tl-success");
        scrollback.print(`Valeur p      : ${TH.pyExp(p, 4)}`, "tl-success");

        if (p < 0.05) {
            scrollback.print("-> Différence globale significative. Lancement du test post-hoc...", "tl-success");
            scrollback.print("", "");
            await scrollback.thinking("test post-hoc de Tukey HSD");
            const rows = tukeyHsd(scores);
            scrollback.print("=== COMPARAISONS PAR PAIRES (TUKEY HSD) ===", "tl-highlight");
            scrollback.print("Groupes : 0=Bush, 1=Obama, 2=Trump", "tl-info");
            scrollback.print("Pairwise Group Comparisons (95.0% Confidence Interval)", "tl-info");
            scrollback.print("Comparison  Statistic  p-value  Lower CI  Upper CI", "tl-info");
            for (const r of rows) {
                scrollback.print(` (${r.i} - ${r.j}) ${TH.rjust(TH.pyFixed(r.diff, 3), 10)}${TH.rjust(TH.pyFixed(r.p, 3), 10)}${TH.rjust(TH.pyFixed(r.lo, 3), 10)}${TH.rjust(TH.pyFixed(r.hi, 3), 10)}`, "tl-info");
            }
        } else {
            scrollback.print("-> Aucune différence significative globale (p >= 0.05).", "tl-warn");
        }
    }

    registerTerminalScript({
        id: "uber-anova",
        pill: "corpus_uber_p.js",
        command: "./corpus-uber-p.py",
        ready: true,
        intro: [
            { text: "Portage JS de corpus-uber-p.py — index Über par blocs, ANOVA puis Tukey HSD entre Bush, Obama et Trump.", cls: "tl-comment" },
            { text: "Sélectionnez un dossier par président (sous-dossiers inclus). Lecture locale : rien n'est envoyé.", cls: "tl-comment" }
        ],
        renderForm,
        run
    });
})();
