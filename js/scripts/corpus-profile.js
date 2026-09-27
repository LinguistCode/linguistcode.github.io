/**--corpus-profile.js--
 * -----------------------------------------------------------------
 * tokens, types et index Über d'un dossier de discours (.txt, sous-dossiers compris), 
 * avec tokenisation regex ([a-zA-ZÀ-ÿ]+ sur le texte en minuscules) et le
 * même export JSON.
 * -------------------------------------------------------------
 */

(function () {
    const REGEX_MOTS = /[a-zA-ZÀ-ÿ]+/g;

    function renderForm() {
        return `
        <div class="input-group">
            <label class="text-xs mb-1 block opacity-80">> Dossier du corpus (sous-dossiers inclus)</label>
            <input type="file" id="cp-folder" class="terminal-input" webkitdirectory directory multiple>
        </div>
        <button id="run-btn" class="terminal-btn w-full">EXECUTE --corpus-profile</button>`;
    }

    async function run(scrollback) {
        const all = Array.from(document.getElementById("cp-folder").files || []);
        if (all.length === 0) {
            scrollback.print("[ERROR] Veuillez sélectionner un dossier.", "tl-error");
            return;
        }
        const folder = TH.rootFolderName(all);
        const fichiers = TH.walkOrder(all.filter(TH.isTxt));

        scrollback.print(`Analyse de ${fichiers.length} fichier(s) en cours...`, "tl-info");
        scrollback.print("", "");

        let totalTokens = 0;
        const types = new Set();

        for (let i = 0; i < fichiers.length; i++) {
            const index = i + 1;
            const f = fichiers[i];
            if (index % 50 === 0) {
                scrollback.print(`Progression : ${index} / ${fichiers.length} fichiers analysés...`, "tl-comment");
                await TH.yieldToBrowser();
            }
            try {
                const contenu = (await TH.readText(f, "strict")).toLowerCase();
                const mots = contenu.match(REGEX_MOTS) || [];
                totalTokens += mots.length;
                for (const m of mots) types.add(m);
            } catch (e) {
                if (e.isDecodeError) scrollback.print(`Fichier ignoré (problème d'encodage) : ${f.name}`, "tl-warn");
                else scrollback.print(`Erreur lors de la lecture de ${f.name} : ${e.message}`, "tl-error");
            }
        }

        const nombreTypes = types.size;
        let uber = null;
        if (totalTokens > 0 && nombreTypes > 0) {
            const logN = Math.log(totalTokens);
            const logV = Math.log(nombreTypes);
            if (logN !== logV) {
                uber = TH.pyRound((logN ** 2) / (logN - logV), 4);
            } else {
                scrollback.print("Avertissement : Le nombre de types est égal au nombre de tokens.", "tl-warn");
            }
        }

        const resultats = {
            dossier_analyse: folder,
            fichiers_traites: fichiers.length,
            total_tokens: totalTokens,
            total_types: nombreTypes,
            uber_index: uber
        };

        scrollback.print("", "");
        scrollback.print("=== RÉSULTATS DE L'ANALYSE ===", "tl-highlight");
        scrollback.print(`Tokens : ${TH.pyThousands(totalTokens, " ")}`, "tl-success");
        scrollback.print(`Types  : ${TH.pyThousands(nombreTypes, " ")}`, "tl-success");
        if (uber) scrollback.print(`Uber Index : ${TH.pyFloatRepr(uber)}`, "tl-success");
        scrollback.print("", "");
        TH.appendDownloadLine("Export JSON", `profil_${folder || "corpus"}.json`,
            new Blob([TH.pyJsonDump(resultats)], { type: "application/json" }));
    }

    registerTerminalScript({
        id: "corpus-profile",
        pill: "corpus_profile.js",
        command: "./corpus-profile-maker.py",
        ready: true,
        intro: [
            { text: "Portage JS de corpus-profile-maker.py — tokens, types et index Über d'un dossier de discours.", cls: "tl-comment" },
            { text: "Tokenisation regex identique au script Python. Le dossier est lu localement, rien n'est envoyé.", cls: "tl-comment" }
        ],
        renderForm,
        run
    });
})();
