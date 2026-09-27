/** -- full-cleaner.js
* -------------------------------------------------------------
 * Nettoyage des fichiers bruts de l'American Presidency Project. Pour chaque .txt du dossier choisi :
 *   - renommage "Initiale - date - titre.txt" (B / O / T, X si inconnu),
 *   - suppression des 5 lignes d'en-tête,
 *   - suppression des crochets de réaction du public ([Laughter]...),
 *   - relevé des marqueurs "President (Bush|Obama|Trump)." / ":",
 *   - relevé des autres crochets, à vérifier à la main.
* -------------------------------------------------------------
 */

(function () {
    const CROWD_BRACKETS = [
        "laughter", "applause", "inaudible", "booing", "boos", "mild cheering",
        "cheers and applause", "cheering", "cheers", "cheer", "laugh", "laughs",
        "laughters", "singing", "shouting", "shouts", "shout",
        "chanting", "yelling", "chants", "yells"
    ];
    const CROWD_SET = new Set(CROWD_BRACKETS);

    // \b Unicode de Python émulé par une assertion arrière
    const REGEX_PRESIDENT = /((?<![\p{L}\p{N}_])(?:The\s+)?President(?:\s+(?:Bush|Obama|Trump))?[.:])/giu;
    const REGEX_BRACKETS = /\[(.*?)\]/g;
    const REGEX_DELETE = new RegExp("\\[\\s*(" + CROWD_BRACKETS.join("|") + ")\\s*\\]", "giu");

    // Python str.strip()
    const pyStrip = (s) => s.replace(/^[\s\x1c-\x1f\x85]+|[\s\x1c-\x1f\x85]+$/gu, "");

    function renderForm() {
        return `
        <div class="input-group">
            <label class="text-xs mb-1 block opacity-80">> Dossier des discours bruts (fichiers .txt à la racine du dossier)</label>
            <input type="file" id="fc-folder" class="terminal-input" webkitdirectory directory multiple>
        </div>
        <button id="run-btn" class="terminal-btn w-full">EXECUTE --full-clean</button>`;
    }

    async function run(scrollback) {
        const all = Array.from(document.getElementById("fc-folder").files || []);
        const fichiers = TH.topLevelOnly(all).filter(TH.isTxt)
            .sort((a, b) => TH.ntfsCompare(a.name, b.name));
        if (fichiers.length === 0) {
            scrollback.print("Aucun discours trouvé dans le dossier. Vérifier le chemin d'accès.", "tl-error");
            return;
        }

        try {
            await scrollback.thinking("chargement de JSZip");
            await TH.loadScriptOnce(TH.JSZIP_URL, "JSZip");
        } catch (e) {
            scrollback.print(`[ERROR] ${e.message}`, "tl-error");
            return;
        }

        const zip = new JSZip();
        const presidentMarker = {};
        const oddBrackets = {};
        const produits = new Map(); // nom de sortie -> fichier source (repère les collisions)
        let nbCourts = 0;

        for (let i = 0; i < fichiers.length; i++) {
            const f = fichiers[i];
            let lignes;
            try {
                lignes = TH.readlines(await TH.readText(f, "strict"));
            } catch (e) {
                scrollback.print(`Erreur d'encodage avec le fichier : ${f.name}`, "tl-error");
                continue;
            }
            if (lignes.length < 5) { nbCourts++; continue; }

            const premiere = lignes[0].toLowerCase();
            let initiale = "X";
            if (premiere.includes("bush")) initiale = "B";
            else if (premiere.includes("obama")) initiale = "O";
            else if (premiere.includes("trump")) initiale = "T";

            const date = pyStrip(lignes[2]);
            const titre = Array.from(pyStrip(lignes[4])).slice(0, 30).join("");
            const dateP = date.replace(/[\\/*?:"<>|]/g, "-");
            const titreP = titre.replace(/[\\/*?:"<>|]/g, "");
            const nouveauNom = `${initiale} - ${dateP} - ${titreP}.txt`;

            const contenu = lignes.slice(5).join("");

            for (const expr of contenu.match(REGEX_PRESIDENT) || []) {
                if (!(expr in presidentMarker)) presidentMarker[expr] = [];
                if (!presidentMarker[expr].includes(nouveauNom)) presidentMarker[expr].push(nouveauNom);
            }

            const crochets = [...contenu.matchAll(REGEX_BRACKETS)].map(m => m[1]);
            const inattendus = crochets.filter(c => !CROWD_SET.has(pyStrip(c).toLowerCase()));
            if (inattendus.length) oddBrackets[nouveauNom] = inattendus;

            const nettoye = contenu.replace(REGEX_DELETE, "");

            if (produits.has(nouveauNom)) {
                scrollback.print(`[attention] ${f.name} écrase ${produits.get(nouveauNom)} (même nom : ${nouveauNom})`, "tl-warn");
            }
            produits.set(nouveauNom, f.name);
            zip.file(nouveauNom, nettoye);
            scrollback.print(`Success : ${nouveauNom} created`, "tl-success");
            if (i % 25 === 24) await TH.yieldToBrowser();
        }

        zip.file("dict_president.json", TH.pyJsonDump(presidentMarker));
        zip.file("dict_other_brackets.json", TH.pyJsonDump(oddBrackets));

        scrollback.print("", "");
        scrollback.print("Opération terminée.", "tl-highlight");
        if (nbCourts) scrollback.print(`${nbCourts} fichier(s) ignoré(s) : moins de 5 lignes.`, "tl-comment");
        scrollback.print(`Rapport Président : ${Object.keys(presidentMarker).length} expression(s) distincte(s)`, "tl-info");
        scrollback.print(`Rapport Crochets  : ${Object.keys(oddBrackets).length} fichier(s) avec crochets inattendus`, "tl-info");

        await scrollback.thinking("compression de l'archive");
        const blob = await zip.generateAsync({ type: "blob" });
        TH.appendDownloadLine("Corpus nettoyé + rapports JSON", "corpus_nettoye.zip", blob);
    }

    registerTerminalScript({
        id: "full-cleaner",
        pill: "full_cleaner.js",
        command: "./full-cleaner.py",
        ready: true,
        intro: [
            { text: "Portage JS de full-cleaner.py — renommage, suppression des en-têtes et des crochets de réaction, rapports JSON.", cls: "tl-comment" },
            { text: "Vos fichiers ne sont ni modifiés ni envoyés : le résultat est proposé en archive .zip.", cls: "tl-comment" }
        ],
        renderForm,
        run
    });
})();
