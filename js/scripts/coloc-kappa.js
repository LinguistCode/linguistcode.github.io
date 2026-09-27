/**--coloc-kappa.js--
 * -------------------------------------------------------------
 * compare la colonne "Valence" (étiquette produite par coloc_eval.py) et la colonne "Verification"(annotation manuelle) d'un classeur .xlsx. 
 * puis calcule le taux d'accord, le kappa de Cohen (grille de Landis & Koch 1977), la matrice de confusion et le détail des désaccords.
 * -------------------------------------------------------------
 */

(function () {
    function extraireLabel(valeur) {
        if (valeur === null || valeur === undefined) return null;
        const texte = String(valeur).trim();
        if (!texte) return null;
        const m = texte.match(/^([A-Za-zÀ-ÿ]+(?:\s[A-Za-zÀ-ÿ]+)?)/);
        if (!m) return texte;
        return m[1].trim();
    }

    function trouverColonne(ws, range, nom) {
        for (let c = range.s.c; c <= range.e.c; c++) {
            const cell = ws[XLSX.utils.encode_cell({ r: 0, c })];
            const entete = cell ? cell.v : null;
            if (entete && String(entete).toLowerCase().includes(nom.toLowerCase())) return c;
        }
        return null;
    }

    // Counter.most_common() : tri décroissant, égalités dans l'ordre d'apparition
    function mostCommon(keys) {
        const m = new Map();
        for (const k of keys) m.set(k, (m.get(k) || 0) + 1);
        return [...m.entries()].sort((a, b) => b[1] - a[1]);
    }

    function kappaCohen(paires) {
        const n = paires.length;
        if (n === 0) return null;
        const accordObserve = paires.filter(([a, m]) => a === m).length / n;
        const labels = [...new Set(paires.flat())].sort(TH.cmpCodePoints);
        const auto = new Map(), manuel = new Map();
        for (const [a, m] of paires) {
            auto.set(a, (auto.get(a) || 0) + 1);
            manuel.set(m, (manuel.get(m) || 0) + 1);
        }
        const accordAttendu = labels.reduce((s, l) => s + ((auto.get(l) || 0) / n) * ((manuel.get(l) || 0) / n), 0);
        if (accordAttendu === 1) return 1.0;
        return (accordObserve - accordAttendu) / (1 - accordAttendu);
    }

    function interpretationKappa(k) {
        if (k < 0) return "désaccord (pire qu'un accord aléatoire)";
        if (k < 0.20) return "accord très faible";
        if (k < 0.40) return "accord faible";
        if (k < 0.60) return "accord modéré";
        if (k < 0.80) return "accord substantiel";
        return "accord quasi parfait";
    }

    function renderForm() {
        return `
        <div class="input-group">
            <label class="text-xs mb-1 block opacity-80">> Classeur annoté (.xlsx, colonnes "Valence" et "Verification")</label>
            <input type="file" id="ck-file" accept=".xlsx,.xls" class="terminal-input">
        </div>
        <button id="run-btn" class="terminal-btn w-full">EXECUTE --kappa</button>`;
    }

    async function run(scrollback) {
        const file = document.getElementById("ck-file").files[0];
        if (!file) {
            scrollback.print("Usage : python comparer_annotations.py fichier.xlsx", "tl-error");
            scrollback.print("[ERROR] Veuillez sélectionner un fichier .xlsx.", "tl-error");
            return;
        }

        let ws, range;
        try {
            await scrollback.thinking("lecture du classeur");
            await TH.loadScriptOnce(TH.SHEETJS_URL, "XLSX");
            const wb = XLSX.read(new Uint8Array(await file.arrayBuffer()), { type: "array" });
            const views = wb.Workbook && wb.Workbook.WBView;
            const active = (views && views[0] && views[0].activeTab) || 0;
            ws = wb.Sheets[wb.SheetNames[active]] || wb.Sheets[wb.SheetNames[0]];
            range = XLSX.utils.decode_range(ws["!ref"] || "A1:A1");
            range.s.c = 0;
        } catch (e) {
            scrollback.print(`[ERROR] Lecture impossible : ${e.message}`, "tl-error");
            return;
        }

        const colValence = trouverColonne(ws, range, "Valence");
        let colVerif = trouverColonne(ws, range, "Verification");
        if (colVerif === null) colVerif = trouverColonne(ws, range, "Vérification");
        if (colValence === null || colVerif === null) {
            scrollback.print("Erreur : impossible de trouver les colonnes 'Valence' et/ou 'Verification' (vérifie l'en-tête en ligne 1).", "tl-error");
            return;
        }

        const cellValue = (r, c) => {
            const cell = ws[XLSX.utils.encode_cell({ r, c })];
            return cell ? cell.v : null;
        };

        const paires = [];
        let lignesIgnorees = 0;
        for (let r = 1; r <= range.e.r; r++) {
            const auto = extraireLabel(cellValue(r, colValence));
            const manuel = extraireLabel(cellValue(r, colVerif));
            if (auto === null || manuel === null) continue;
            if (auto === "Non trouvé") { lignesIgnorees++; continue; }
            paires.push([auto, manuel]);
        }

        if (paires.length === 0) {
            scrollback.print("Aucune paire (Valence, Verification) exploitable trouvée.", "tl-error");
            return;
        }

        const n = paires.length;
        const accords = paires.filter(([a, m]) => a === m);
        const desaccords = paires.filter(([a, m]) => a !== m);
        const tauxAccord = accords.length / n * 100;
        const kappa = kappaCohen(paires);

        const labels = [...new Set(paires.flat())].sort(TH.cmpCodePoints);
        const matrice = new Map(labels.map(l => [l, new Map()]));
        for (const [a, m] of paires) matrice.get(m).set(a, (matrice.get(m).get(a) || 0) + 1);

        scrollback.print("", "");
        scrollback.print(`Fichier : ${file.name}`, "tl-info");
        scrollback.print(`Lignes comparées : ${n} (+ ${lignesIgnorees} ignorées car 'Non trouvé' par le script)`, "tl-info");
        scrollback.print("", "");
        scrollback.print(`Taux d'accord simple : ${TH.pyFixed(tauxAccord, 1)} %  (${accords.length}/${n})`, "tl-success");
        scrollback.print(`Kappa de Cohen        : ${TH.pyFixed(kappa, 3)}  (${interpretationKappa(kappa)})`, "tl-success");
        scrollback.print("", "");
        scrollback.print("Matrice de confusion (lignes = annotation manuelle, colonnes = script) :", "tl-highlight");
        scrollback.print(TH.ljust("", 14) + labels.map(l => TH.ljust(l, 12)).join(""), "tl-info");
        for (const lm of labels) {
            let ligne = TH.ljust(lm, 14);
            for (const la of labels) ligne += TH.ljust(String(matrice.get(lm).get(la) || 0), 12);
            scrollback.print(ligne, "tl-info");
        }
        scrollback.print("", "");

        if (desaccords.length) {
            scrollback.print(`Détail des ${desaccords.length} désaccords (script -> manuel) :`, "tl-highlight");
            for (const [key, c] of mostCommon(desaccords.map(([a, m]) => `${a}\u0000${m}`))) {
                const [a, m] = key.split("\u0000");
                scrollback.print(`  ${a} -> ${m} : ${c} cas`, "tl-warn");
            }
        }
    }

    registerTerminalScript({
        id: "coloc-kappa",
        pill: "coloc_eval_kappa.js",
        command: "./coloc_eval_kappa.py fichier.xlsx",
        ready: true,
        intro: [
            { text: "Portage JS de coloc_eval_kappa.py — accord entre la valence automatique (coloc_eval.py) et l'annotation manuelle.", cls: "tl-comment" },
            { text: "Déposez le classeur annoté (.xlsx) : il est lu localement, rien n'est envoyé.", cls: "tl-comment" }
        ],
        renderForm,
        run
    });
})();
