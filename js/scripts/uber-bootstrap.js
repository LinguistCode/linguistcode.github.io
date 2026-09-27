/**-- uber-bootstrap.js--
* -------------------------------------------------------------
 * index Über (log10) de deux textes, rééchantillonnage bootstrap des tokens (avec remise), 
 * intervalles de confiance à 95 % et p-value unilatérale (H0 : Texte 2 ≤ Texte 1).
 *
 * /!\ le générateur aléatoire n'est pas celui de numpy (graine 42 dans les deux cas, mais algorithmes différents). 
 * Les valeurs bootstrap diffèrent, sans effet sur les conclusions. 
 * Tout le reste (tokenisation, formules, percentiles, écart-type) reproduit le script Py à l'identique.
 * -------------------------------------------------------------
 */

(function () {
    // \b de Python est Unicode ; celui de JavaScript ne l'est pas -> émulation.
    const W = "[\\p{L}\\p{N}_]";
    const B = `(?:(?<=${W})(?!${W})|(?<!${W})(?=${W}))`;
    const TOKEN = new RegExp(`${B}[a-zA-ZÀ-ÿ'\\-]+${B}`, "gu");

    function tokenize(text) {
        return text.toLowerCase().match(TOKEN) || [];
    }

    function uberIndex(T, V) {
        if (T === 0 || V === 0) throw new Error("Empty token list.");
        const logT = Math.log10(T), logV = Math.log10(V);
        if (logT === logV) throw new Error("log T == log V: U is undefined (all tokens are unique).");
        return (logT ** 2) / (logT - logV);
    }

    // Tokens -> identifiants entiers, pour compter les types d'un échantillon
    // en O(T) sans construire de Set à chaque itération.
    function encode(tokens) {
        const map = new Map();
        const ids = new Uint32Array(tokens.length);
        tokens.forEach((t, i) => {
            let id = map.get(t);
            if (id === undefined) { id = map.size; map.set(t, id); }
            ids[i] = id;
        });
        return { ids, nTypes: map.size };
    }

    async function bootstrapUber(tokens, nIter, seed, onProgress) {
        const rand = TH.seededRandom(seed);
        const { ids, nTypes } = encode(tokens);
        const T = ids.length;
        const stamp = new Uint32Array(nTypes);
        const results = [];
        for (let it = 1; it <= nIter; it++) {
            let v = 0;
            for (let i = 0; i < T; i++) {
                const id = ids[Math.floor(rand() * T)];
                if (stamp[id] !== it) { stamp[id] = it; v++; }
            }
            const logT = Math.log10(T), logV = Math.log10(v);
            if (logT !== logV) results.push((logT ** 2) / (logT - logV));
            if (it % 250 === 0) {
                onProgress(it);
                await TH.yieldToBrowser();
            }
        }
        return results;
    }

    function report(scrollback, label, tokens, boot) {
        const uObs = uberIndex(tokens.length, new Set(tokens).size);
        scrollback.print("", "");
        scrollback.print(label, "tl-highlight");
        scrollback.print(`  Tokens  : ${TH.pyThousands(tokens.length)}`, "tl-info");
        scrollback.print(`  Types   : ${TH.pyThousands(new Set(tokens).size)}`, "tl-info");
        scrollback.print(`  U (obs) : ${TH.pyFixed(uObs, 4)}`, "tl-success");
        scrollback.print(`  U (boot): ${TH.pyFixed(TH.mean(boot), 4)} ± ${TH.pyFixed(TH.std(boot), 4)}`, "tl-info");
        scrollback.print(`  95% CI  : [${TH.pyFixed(TH.percentile(boot, 2.5), 4)}, ${TH.pyFixed(TH.percentile(boot, 97.5), 4)}]`, "tl-info");
        return uObs;
    }

    function renderForm() {
        return `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-2">
            <div class="input-group">
                <label class="text-xs mb-1 block opacity-80">> Texte 1 (.txt)</label>
                <input type="file" id="ub-file1" accept=".txt" class="terminal-input">
            </div>
            <div class="input-group">
                <label class="text-xs mb-1 block opacity-80">> Texte 2 (.txt) — celui supposé plus riche</label>
                <input type="file" id="ub-file2" accept=".txt" class="terminal-input">
            </div>
        </div>
        <div class="input-group">
            <label class="text-xs mb-1 block opacity-80">> Itérations bootstrap par texte</label>
            <input type="number" id="ub-iter" class="terminal-input" value="10000" min="100" step="100">
        </div>
        <button id="run-btn" class="terminal-btn w-full">EXECUTE --uber-bootstrap</button>`;
    }

    async function run(scrollback) {
        const f1 = document.getElementById("ub-file1").files[0];
        const f2 = document.getElementById("ub-file2").files[0];
        const nBoot = parseInt(document.getElementById("ub-iter").value, 10);
        if (!f1 || !f2) {
            scrollback.print("Usage: python uber_bootstrap.py <text1> <text2>", "tl-error");
            scrollback.print("[ERROR] Veuillez sélectionner les deux fichiers texte.", "tl-error");
            return;
        }
        if (!(nBoot >= 100)) {
            scrollback.print("[ERROR] Le nombre d'itérations doit être ≥ 100.", "tl-error");
            return;
        }

        let tokens1, tokens2;
        try {
            tokens1 = tokenize(await TH.readText(f1, "strict"));
            tokens2 = tokenize(await TH.readText(f2, "strict"));
            uberIndex(tokens1.length, new Set(tokens1).size);
            uberIndex(tokens2.length, new Set(tokens2).size);
        } catch (e) {
            scrollback.print(`[ERROR] ${e.message}`, "tl-error");
            return;
        }

        const work = (tokens1.length + tokens2.length) * nBoot;
        if (work > 3e8) {
            scrollback.print(`[info] ${TH.pyThousands(work)} tirages au total : le calcul peut prendre un moment.`, "tl-warn");
        }

        scrollback.print(`Running ${TH.pyThousands(nBoot)} bootstrap iterations per text...`, "tl-info");
        const progress = scrollback.print("", "tl-comment");
        const boot1 = await bootstrapUber(tokens1, nBoot, 42, (it) => { progress.textContent = `> Texte 1 : ${it} / ${nBoot}`; });
        const boot2 = await bootstrapUber(tokens2, nBoot, 42, (it) => { progress.textContent = `> Texte 2 : ${it} / ${nBoot}`; });
        progress.textContent = "> bootstrap terminé";

        scrollback.print("", "");
        scrollback.print("=".repeat(50), "tl-comment");
        scrollback.print("UBER INDEX — BOOTSTRAP RESULTS", "tl-highlight");
        scrollback.print("=".repeat(50), "tl-comment");

        const u1 = report(scrollback, "Text 1 — " + f1.name, tokens1, boot1);
        const u2 = report(scrollback, "Text 2 — " + f2.name, tokens2, boot2);

        const n = Math.min(boot1.length, boot2.length);
        const bootDiff = [];
        for (let i = 0; i < n; i++) bootDiff.push(boot2[i] - boot1[i]);
        const pVal = bootDiff.filter(d => d <= 0).length / n;

        scrollback.print("", "");
        scrollback.print("--- Difference (Text 2 − Text 1) ---", "tl-highlight");
        scrollback.print(`  Observed diff : ${TH.pyFixed(u2 - u1, 4)}`, "tl-info");
        scrollback.print(`  Bootstrap diff: ${TH.pyFixed(TH.mean(bootDiff), 4)} ± ${TH.pyFixed(TH.std(bootDiff), 4)}`, "tl-info");
        scrollback.print(`  95% CI        : [${TH.pyFixed(TH.percentile(bootDiff, 2.5), 4)}, ${TH.pyFixed(TH.percentile(bootDiff, 97.5), 4)}]`, "tl-info");
        scrollback.print(`  p-value (H0: T2 ≤ T1): ${TH.pyFixed(pVal, 4)}`, "tl-info");

        let verdict, cls;
        if (pVal < 0.001) { verdict = "SIGNIFICANT (p < 0.001)"; cls = "tl-success"; }
        else if (pVal < 0.05) { verdict = `SIGNIFICANT (p = ${TH.pyFixed(pVal, 4)})`; cls = "tl-success"; }
        else { verdict = `NOT significant (p = ${TH.pyFixed(pVal, 4)})`; cls = "tl-warn"; }
        scrollback.print("", "");
        scrollback.print(`  Verdict: ${verdict}`, cls);
        scrollback.print("=".repeat(50), "tl-comment");
    }

    registerTerminalScript({
        id: "uber-bootstrap",
        pill: "uber_bootstrap.js",
        command: "./uber_bootstrap.py <text1> <text2>",
        ready: true,
        intro: [
            { text: "Portage JS de uber_bootstrap.py — l'index Über du texte 2 est-il significativement plus élevé que celui du texte 1 ?", cls: "tl-comment" },
            { text: "Test unilatéral : l'ordre des fichiers compte. Générateur aléatoire différent de numpy (graine 42) : écarts minimes possibles.", cls: "tl-comment" }
        ],
        renderForm,
        run
    });
})();
