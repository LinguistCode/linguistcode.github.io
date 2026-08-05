/**
 * corpus-stats.js
 * -----------------------------------------------------------------
 * Portage JS de helper_v2.py.
 * Regroupe les 3 fonctionnalités du menu Python original :
 *   1. Fréquence relative
 *   2. Index Über
 *   3. Log-vraisemblance (G²) et p-value
 * en un seul module de terminal, avec un sous-sélecteur interne
 * pour reproduire le menu du script source.
 */

(function () {
    // Corpus codés en dur, identiques au dictionnaire `corpora` du script Python
    const CORPORA = {
        "1": { name: "Bush Corpus", tokens: 3439334 },
        "2": { name: "Obama Corpus", tokens: 3471270 },
        "3": { name: "Trump Corpus", tokens: 1626297 },
        "4": { name: "Full Corpus", tokens: 8536901 }
    };

    const corpusOptionsHtml = Object.entries(CORPORA)
        .map(([k, v]) => `<option value="${k}">${v.name} (${v.tokens.toLocaleString('fr-FR')} tokens)</option>`)
        .join("");

    // ---------- Approximation de la fonction de survie du Chi² à 1 ddl ----------
    // (équivalent JS de scipy.stats.chi2.sf(g2, 1), même formule que dans la V1 du terminal)
    function chi2_sf_df1(x) {
        if (x <= 0) return 1.0;
        const z = Math.sqrt(x / 2);
        const t = 1.0 / (1.0 + 0.5 * z);
        return t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 + t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))));
    }

    // ---------- 1. Fréquence relative ----------
    function renderRelativeFreqForm() {
        return `
        <div class="input-group">
            <label class="text-xs mb-1 block opacity-80">> Corpus</label>
            <select id="rf-corpus" class="terminal-input">${corpusOptionsHtml}</select>
        </div>
        <div class="input-group">
            <label class="text-xs mb-1 block opacity-80">> Base de référence (ex: 10000, 100000)</label>
            <input type="number" id="rf-scale" class="terminal-input" placeholder="ex: 10000" value="10000">
        </div>
        <div class="input-group">
            <label class="text-xs mb-1 block opacity-80">> Occurrences brutes (séparées par des points-virgules)</label>
            <input type="text" id="rf-raw" class="terminal-input" placeholder="ex: 45; 12; 3">
        </div>
        <button id="run-btn" class="terminal-btn w-full">EXECUTE --relative-frequency</button>`;
    }

    async function runRelativeFreq(scrollback) {
        const c = document.getElementById("rf-corpus").value;
        const scale = parseFloat(document.getElementById("rf-scale").value);
        const rawInput = document.getElementById("rf-raw").value.trim();

        if (!rawInput || isNaN(scale)) {
            scrollback.print("[ERROR] Veuillez renseigner la base de référence et au moins une occurrence brute.", "tl-error");
            return;
        }

        const rawValues = rawInput.split(";")
            .map(v => v.trim())
            .filter(v => v.length > 0)
            .map(v => parseInt(v, 10));

        if (rawValues.some(isNaN)) {
            scrollback.print("[ERROR] Occurrences brutes invalides — utilisez des entiers séparés par des points-virgules (ex: 45; 12; 3).", "tl-error");
            return;
        }

        const n = CORPORA[c].tokens;
        await scrollback.thinking(`calcul sur ${CORPORA[c].name} (${n.toLocaleString('fr-FR')} tokens)`);

        const results = rawValues.map(raw => {
            const rf = (raw / n) * scale;
            return `(${raw}) --> ${rf.toFixed(2)}`;
        });

        scrollback.print("", "");
        scrollback.print("[RÉSULTATS]", "tl-highlight");
        scrollback.print(`-> Fréquence relative : ${results.join("; ")}`, "tl-success");
    }

    // ---------- 2. Index Über ----------
    function renderUberForm() {
        return `
        <div class="input-group">
            <label class="text-xs mb-1 block opacity-80">> Nombre total de tokens</label>
            <input type="number" id="ub-tokens" class="terminal-input" placeholder="ex: 12000">
        </div>
        <div class="input-group">
            <label class="text-xs mb-1 block opacity-80">> Nombre de types uniques</label>
            <input type="number" id="ub-types" class="terminal-input" placeholder="ex: 2400">
        </div>
        <button id="run-btn" class="terminal-btn w-full">EXECUTE --uber-index</button>`;
    }

    async function runUber(scrollback) {
        const tokens = parseFloat(document.getElementById("ub-tokens").value);
        const types = parseFloat(document.getElementById("ub-types").value);

        if (isNaN(tokens) || isNaN(types)) {
            scrollback.print("[ERROR] Veuillez renseigner le nombre de tokens et de types.", "tl-error");
            return;
        }

        await scrollback.thinking("calcul de l'index Über");

        if (tokens > 1 && types > 1 && tokens !== types) {
            const u = Math.pow(Math.log(tokens), 2) / (Math.log(tokens) - Math.log(types));
            scrollback.print("", "");
            scrollback.print("[RÉSULTATS]", "tl-highlight");
            scrollback.print(`-> Index Über : ${u.toFixed(2)}`, "tl-success");
        } else {
            scrollback.print("-> Erreur : les tokens et types doivent être supérieurs à 1 et différents.", "tl-error");
        }
    }

    // ---------- 3. Log-vraisemblance (G²) et p-value ----------
    function renderLogLikelihoodForm() {
        return `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
                <p class="text-sm mb-3 opacity-70">>> CORPUS_1</p>
                <div class="input-group">
                    <label class="text-xs mb-1 block opacity-80">> Corpus</label>
                    <select id="ll-corpus1" class="terminal-input">${corpusOptionsHtml}</select>
                </div>
                <div class="input-group">
                    <label class="text-xs mb-1 block opacity-80">> Occurrences brutes ciblées</label>
                    <input type="number" id="ll-occ1" class="terminal-input" placeholder="ex: 120">
                </div>
            </div>
            <div>
                <p class="text-sm mb-3 opacity-70">>> CORPUS_2</p>
                <div class="input-group">
                    <label class="text-xs mb-1 block opacity-80">> Corpus</label>
                    <select id="ll-corpus2" class="terminal-input">${corpusOptionsHtml}</select>
                </div>
                <div class="input-group">
                    <label class="text-xs mb-1 block opacity-80">> Occurrences brutes ciblées</label>
                    <input type="number" id="ll-occ2" class="terminal-input" placeholder="ex: 80">
                </div>
            </div>
        </div>
        <button id="run-btn" class="terminal-btn w-full">EXECUTE --log-likelihood</button>`;
    }

    function setDefaultLLCorpora(formzone) {
        // reproduit un choix par défaut pratique : Bush vs Obama (comme un premier essai typique)
        const c1 = formzone.querySelector("#ll-corpus1");
        const c2 = formzone.querySelector("#ll-corpus2");
        if (c1 && c2) {
            c1.value = "1";
            c2.value = "2";
        }
    }

    async function runLogLikelihood(scrollback) {
        const c1 = document.getElementById("ll-corpus1").value;
        const c2 = document.getElementById("ll-corpus2").value;
        const o1 = parseFloat(document.getElementById("ll-occ1").value);
        const o2 = parseFloat(document.getElementById("ll-occ2").value);

        if (isNaN(o1) || isNaN(o2)) {
            scrollback.print("[ERROR] SYSTÈME ARRÊTÉ : veuillez remplir les deux champs d'occurrences.", "tl-error");
            return;
        }

        if (c1 === c2) {
            scrollback.print("[ERROR] Choisissez deux corpus distincts pour la comparaison.", "tl-error");
            return;
        }

        const n1 = CORPORA[c1].tokens;
        const n2 = CORPORA[c2].tokens;

        await scrollback.thinking("initialisation du module scipy.stats.chi2");
        await scrollback.printTyped(`> comparaison : ${CORPORA[c1].name} vs ${CORPORA[c2].name}`, "tl-info", 10);

        // Tableau de contingence 2x2 complet (méthode standard, Dunning 1993)
        const autre1 = n1 - o1;
        const autre2 = n2 - o2;
        const total_mot = o1 + o2;
        const total_autre = autre1 + autre2;
        const total_n = n1 + n2;

        const e1 = (n1 * total_mot) / total_n;
        const e2 = (n2 * total_mot) / total_n;
        const e_autre1 = (n1 * total_autre) / total_n;
        const e_autre2 = (n2 * total_autre) / total_n;

        let g2 = 0.0;
        const table = [[o1, e1], [o2, e2], [autre1, e_autre1], [autre2, e_autre2]];
        for (const [o, e] of table) {
            if (o > 0 && e > 0) g2 += o * Math.log(o / e);
        }
        g2 *= 2;

        const pVal = chi2_sf_df1(g2);

        scrollback.print("", "");
        scrollback.print("[RÉSULTATS]", "tl-highlight");
        scrollback.print(`-> Log-Likelihood (G²) : ${g2.toFixed(4)}`, "tl-success");
        scrollback.print(`-> p-value             : ${pVal.toExponential(4)}`, "tl-success");
        scrollback.print("", "");

        if (pVal < 0.05) {
            scrollback.print("-> Résultat : différence STATISTIQUEMENT SIGNIFICATIVE (p < 0.05).", "tl-success");
        } else {
            scrollback.print("-> Résultat : différence NON SIGNIFICATIVE (p >= 0.05).", "tl-warn");
        }
    }

    // ---------- Sous-menu : reproduit le menu 1/2/3 du script Python ----------
    const SUBTOOLS = {
        "relative-freq": {
            label: "Fréquence relative",
            renderForm: renderRelativeFreqForm,
            run: runRelativeFreq
        },
        "uber-index": {
            label: "Index Über",
            renderForm: renderUberForm,
            run: runUber
        },
        "log-likelihood": {
            label: "Log-vraisemblance & p-value",
            renderForm: renderLogLikelihoodForm,
            run: runLogLikelihood,
            onFormReady: setDefaultLLCorpora
        }
    };

    function renderSubmenu(activeKey) {
        const tabs = Object.entries(SUBTOOLS).map(([key, tool]) => `
            <button type="button" class="subtool-tab ${key === activeKey ? 'active' : ''}" data-subtool="${key}">
                ${tool.label}
            </button>`).join("");
        return `<div class="subtool-tabs">${tabs}</div>`;
    }

    // ---------- Entrée du registre : orchestre le sous-menu + délègue à l'outil actif ----------
    let currentSubtool = "relative-freq";

    registerTerminalScript({
        id: "corpus-stats",
        pill: "corpus_stats.js",
        command: "./corpus_stats.py  # menu interactif",
        ready: true,
        selfManagesRunButton: true, // ce script a un sous-menu ; il gère lui-même le bouton EXECUTE
        intro: [
            { text: "Portage JS de helper_v2.py — 4 corpus (Bush, Obama, Trump, Full) codés en dur.", cls: "tl-comment" },
            { text: "Sélectionnez une fonctionnalité ci-dessous (équivalent du menu 1/2/3 du script Python).", cls: "tl-comment" }
        ],
        renderForm() {
            return `
                ${renderSubmenu(currentSubtool)}
                <div id="corpus-stats-subform" class="mt-5">
                    ${SUBTOOLS[currentSubtool].renderForm()}
                </div>`;
        },
        onFormReady(formzone) {
            wireSubtool(formzone);
        },
        async run(scrollback) {
            // no-op : le bouton EXECUTE réel est branché par sous-outil dans wireSubtool()
        }
    });

    function wireSubtool(formzone) {
        formzone.querySelectorAll(".subtool-tab").forEach(tab => {
            tab.classList.toggle("active", tab.dataset.subtool === currentSubtool);
            tab.addEventListener("click", () => {
                currentSubtool = tab.dataset.subtool;
                formzone.innerHTML = `
                    ${renderSubmenu(currentSubtool)}
                    <div id="corpus-stats-subform" class="mt-5">
                        ${SUBTOOLS[currentSubtool].renderForm()}
                    </div>`;
                wireSubtool(formzone);
            });
        });

        const tool = SUBTOOLS[currentSubtool];
        if (typeof tool.onFormReady === "function") {
            tool.onFormReady(formzone);
        }

        const runBtn = formzone.querySelector("#run-btn");
        if (runBtn) {
            runBtn.addEventListener("click", async () => {
                runBtn.disabled = true;
                const originalLabel = runBtn.textContent;
                runBtn.textContent = "EXECUTING...";
                const scrollback = createScrollback(document.getElementById("terminal-scrollback"));
                await tool.run(scrollback);
                runBtn.disabled = false;
                runBtn.textContent = originalLabel;
            });
        }
    }
})();
