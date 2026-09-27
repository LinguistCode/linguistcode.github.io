/** -- fear-lexicon.js --
 * -------------------------------------------------------------
 * Portage JS de fear_lexicon.py : repère les mots d'un texte présents dans un lexique d'intensité 
 * (NRC Emotion Intensity Lexicon, Mohammad 2018), avec leur fréquence et leur score. 
 * Même lecture du lexique, même tokenisation  et même tri. Le tableau est affiché et téléchargeable (--out).
 * -------------------------------------------------------------
 */

(function () {
    const TOKEN = /[\p{L}\p{Nl}\p{No}]+/gu; // équivalent de [^\W\d_]+ (Python, Unicode)
    const FLOAT = /^[+-]?(?:(?:\d(?:_?\d)*)?\.?\d(?:_?\d)*(?:[eE][+-]?\d(?:_?\d)*)?|\d(?:_?\d)*\.|inf|infinity|nan)$/i;

    // float() de Python (espaces autour tolérés, underscores entre chiffres)
    function pyFloat(s) {
        const t = s.trim();
        if (!t || !FLOAT.test(t)) return null;
        const low = t.toLowerCase().replace(/^[+]/, "");
        if (/^-?(inf|infinity)$/.test(low)) return low.startsWith("-") ? -Infinity : Infinity;
        if (/^-?nan$/.test(low)) return NaN;
        return Number(t.replace(/_/g, ""));
    }

    // repr() de Python pour une chaîne (utilisé dans les avertissements)
    function pyRepr(str) {
        const q = str.includes("'") && !str.includes('"') ? '"' : "'";
        const body = str.replace(/\\/g, "\\\\").replace(/\t/g, "\\t").replace(/\r/g, "\\r").replace(/\n/g, "\\n")
            .replace(new RegExp(q, "g"), "\\" + q);
        return q + body + q;
    }

    function loadLexicon(text, warn) {
        const lexicon = new Map();
        const lines = TH.universalNewlines(text).split("\n");
        if (lines.length && lines[lines.length - 1] === "") lines.pop();
        lines.forEach((line, i) => {
            const lineno = i + 1;
            if (!line.trim()) return;
            let parts = line.split("\t").filter(p => p !== "");
            if (parts.length < 2) parts = line.trim().split(/\s+/).filter(p => p !== "");
            if (parts.length < 2) {
                warn(`[avertissement] ligne ${lineno} ignorée (format invalide): ${pyRepr(line)}`);
                return;
            }
            const word = parts[0];
            const score = pyFloat(parts[parts.length - 1]);
            if (score === null) {
                warn(`[avertissement] ligne ${lineno} ignorée (score non numérique): ${pyRepr(line)}`);
                return;
            }
            lexicon.set(word.toLowerCase(), score);
        });
        return lexicon;
    }

    function renderForm() {
        return `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-2">
            <div class="input-group">
                <label class="text-xs mb-1 block opacity-80">> Lexique (mot [tab] score)</label>
                <input type="file" id="fl-lexicon" accept=".txt,.tsv" class="terminal-input">
            </div>
            <div class="input-group">
                <label class="text-xs mb-1 block opacity-80">> Corpus (texte brut .txt)</label>
                <input type="file" id="fl-corpus" accept=".txt" class="terminal-input">
            </div>
        </div>
        <button id="run-btn" class="terminal-btn w-full">EXECUTE --fear-lexicon</button>`;
    }

    async function run(scrollback) {
        const lexFile = document.getElementById("fl-lexicon").files[0];
        const corpusFile = document.getElementById("fl-corpus").files[0];
        if (!lexFile || !corpusFile) {
            scrollback.print("usage: fear_lexicon.py --lexicon LEXIQUE.txt --corpus CORPUS.txt [--out resultats.tsv]", "tl-error");
            scrollback.print("[ERROR] Veuillez sélectionner le lexique et le corpus.", "tl-error");
            return;
        }

        let lexicon, text;
        try {
            await scrollback.thinking("chargement du lexique");
            lexicon = loadLexicon(await TH.readText(lexFile, "strict"), (m) => scrollback.print(m, "tl-warn"));
            text = await TH.readText(corpusFile, "strict");
        } catch (e) {
            scrollback.print(`[ERROR] ${e.message}`, "tl-error");
            return;
        }

        await scrollback.thinking("tokenisation et recherche dans le lexique");
        const tokens = text.toLowerCase().match(TOKEN) || [];
        const counts = new Map();
        for (const t of tokens) counts.set(t, (counts.get(t) || 0) + 1);

        const matches = [];
        for (const [word, count] of counts) {
            if (lexicon.has(word)) matches.push([word, count, lexicon.get(word)]);
        }
        matches.sort((a, b) => (b[1] - a[1]) || TH.cmpCodePoints(a[0], b[0]));

        let out = "\n" + TH.ljust("mot", 15) + TH.ljust("occurrences", 15) + TH.ljust("score", 10) + "\n";
        for (const [w, c, s] of matches) {
            out += TH.ljust(w, 15) + TH.ljust(String(c), 15) + TH.ljust(TH.pyFloatRepr(s), 10) + "\n";
        }

        scrollback.print("", "");
        scrollback.print("[RÉSULTATS]", "tl-highlight");
        const MAX_SHOWN = 60;
        const outLines = out.split("\n").slice(1, -1);
        outLines.slice(0, MAX_SHOWN + 1).forEach((l, i) => scrollback.print(l, i === 0 ? "tl-highlight" : "tl-info"));
        if (outLines.length > MAX_SHOWN + 1) {
            scrollback.print(`... (${outLines.length - MAX_SHOWN - 1} lignes supplémentaires dans le fichier téléchargeable)`, "tl-comment");
        }

        const totalMatches = matches.reduce((s, m) => s + m[1], 0);
        scrollback.print("", "");
        scrollback.print(`[info] ${matches.length} mots-clés trouvés dans le lexique (${totalMatches} occurrences sur ${tokens.length} tokens)`, "tl-success");
        scrollback.print("-".repeat(30), "tl-comment");
        TH.appendDownloadLine("Résultats (--out)", "resultats.tsv",
            new Blob([out], { type: "text/tab-separated-values;charset=utf-8" }));
    }

    registerTerminalScript({
        id: "fear-lexicon",
        pill: "fear_lexicon.js",
        command: "./fear_lexicon.py --lexicon LEXIQUE.txt --corpus CORPUS.txt",
        ready: true,
        intro: [
            { text: "Portage JS de fear_lexicon.py — mots d'un texte présents dans le NRC Emotion Intensity Lexicon (Mohammad 2018).", cls: "tl-comment" },
            { text: "Utilisez le fichier du lexique limité à une émotion (ex. fear) : avec le fichier complet, seul le dernier score lu par mot est gardé.", cls: "tl-comment" }
        ],
        renderForm,
        run
    });
})();
