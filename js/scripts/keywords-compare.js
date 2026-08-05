/**
 * keywords-compare.js
 * -----------------------------------------------------------------
 * Portage JS de keywords-compare.py.
 * Compare 3 fichiers .xlsx de keywords (ex: top 100 par président),
 * calcule les intersections/différences (logique de Venn), affiche
 * les résultats dans le terminal et propose le même export JSON que
 * le script Python original.
 *
 * Dépendance : SheetJS (xlsx.full.min.js). Chargée dynamiquement au
 * premier lancement si elle n'est pas déjà présente sur la page —
 * aucune modification du HTML n'est nécessaire.
 */

(function () {
    const SHEETJS_URL = "https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js";
    let sheetJsLoading = null;

    function loadSheetJS() {
        if (window.XLSX) return Promise.resolve();
        if (sheetJsLoading) return sheetJsLoading;
        sheetJsLoading = new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = SHEETJS_URL;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error("Impossible de charger SheetJS."));
            document.head.appendChild(script);
        });
        return sheetJsLoading;
    }

    function readWorkbook(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const data = new Uint8Array(e.target.result);
                    const wb = window.XLSX.read(data, { type: "array" });
                    resolve(wb);
                } catch (err) {
                    reject(err);
                }
            };
            reader.onerror = () => reject(new Error(`Échec de lecture du fichier ${file.name}.`));
            reader.readAsArrayBuffer(file);
        });
    }

    // Reproduit charger_keywords_excel() : lit la 1re feuille, extrait la colonne,
    // nettoie (trim + minuscule), retire les vides, renvoie un Set.
    async function loadKeywordsFromExcel(file, columnName) {
        const wb = await readWorkbook(file);
        const sheet = wb.Sheets[wb.SheetNames[0]];
        const rows = window.XLSX.utils.sheet_to_json(sheet, { defval: "" });

        if (rows.length > 0 && !(columnName in rows[0])) {
            throw new Error(`Colonne "${columnName}" introuvable dans ${file.name}.`);
        }

        const set = new Set();
        for (const row of rows) {
            const v = String(row[columnName] ?? "").trim().toLowerCase();
            if (v) set.add(v);
        }
        return set;
    }

    function setDiff(a, ...others) {
        const union = new Set();
        others.forEach(s => s.forEach(v => union.add(v)));
        return new Set([...a].filter(v => !union.has(v)));
    }

    function setIntersect(...sets) {
        const [first, ...rest] = sets;
        return new Set([...first].filter(v => rest.every(s => s.has(v))));
    }

    function setUnion(...sets) {
        const u = new Set();
        sets.forEach(s => s.forEach(v => u.add(v)));
        return u;
    }

    function fmtList(set, maxShown = 30) {
        const arr = [...set].sort();
        if (arr.length === 0) return "(aucun)";
        if (arr.length <= maxShown) return arr.join(", ");
        return arr.slice(0, maxShown).join(", ") + ` … (+${arr.length - maxShown} autres, voir JSON)`;
    }

    function appendDownloadLine(label, filename, jsonStr) {
        const container = document.getElementById("terminal-scrollback");
        const blob = new Blob([jsonStr], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const line = document.createElement("div");
        line.className = "tl-line tl-success";
        line.innerHTML = `-> ${label} : <a href="${url}" download="${filename}" style="color:#58a6ff;text-decoration:underline;">${filename}</a>`;
        container.appendChild(line);
        container.scrollTop = container.scrollHeight;
    }

    function renderForm() {
        return `
        <div class="input-group">
            <label class="text-xs mb-1 block opacity-80">> Nom de la colonne des mots-clés</label>
            <input type="text" id="kc-column" class="terminal-input" value="Item" placeholder="ex: Item">
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-2">
            <div class="input-group">
                <label class="text-xs mb-1 block opacity-80">> Fichier Président 1 (.xlsx)</label>
                <input type="file" id="kc-file1" accept=".xlsx,.xls" class="terminal-input">
            </div>
            <div class="input-group">
                <label class="text-xs mb-1 block opacity-80">> Fichier Président 2 (.xlsx)</label>
                <input type="file" id="kc-file2" accept=".xlsx,.xls" class="terminal-input">
            </div>
            <div class="input-group">
                <label class="text-xs mb-1 block opacity-80">> Fichier Président 3 (.xlsx)</label>
                <input type="file" id="kc-file3" accept=".xlsx,.xls" class="terminal-input">
            </div>
        </div>
        <button id="run-btn" class="terminal-btn w-full">EXECUTE --keywords-compare</button>`;
    }

    async function run(scrollback) {
        const columnName = document.getElementById("kc-column").value.trim() || "Item";
        const f1 = document.getElementById("kc-file1").files[0];
        const f2 = document.getElementById("kc-file2").files[0];
        const f3 = document.getElementById("kc-file3").files[0];

        if (!f1 || !f2 || !f3) {
            scrollback.print("[ERROR] Veuillez sélectionner les 3 fichiers .xlsx.", "tl-error");
            return;
        }

        try {
            await scrollback.thinking("chargement de SheetJS");
            await loadSheetJS();

            await scrollback.thinking("lecture des fichiers .xlsx et extraction de la colonne");
            const [kw1, kw2, kw3] = await Promise.all([
                loadKeywordsFromExcel(f1, columnName),
                loadKeywordsFromExcel(f2, columnName),
                loadKeywordsFromExcel(f3, columnName)
            ]);

            await scrollback.printTyped(
                `> Mots chargés : Président 1 (${kw1.size}), Président 2 (${kw2.size}), Président 3 (${kw3.size})`,
                "tl-info", 6
            );

            const communsTous = setIntersect(kw1, kw2, kw3);
            const specifiquesP1 = setDiff(kw1, kw2, kw3);
            const specifiquesP2 = setDiff(kw2, kw1, kw3);
            const specifiquesP3 = setDiff(kw3, kw1, kw2);
            const partagesP1P2 = setDiff(setIntersect(kw1, kw2), kw3);
            const partagesP2P3 = setDiff(setIntersect(kw2, kw3), kw1);
            const partagesP1P3 = setDiff(setIntersect(kw1, kw3), kw2);

            scrollback.print("", "");
            scrollback.print("[RÉSULTATS]", "tl-highlight");
            scrollback.print(`-> Communs aux trois (${communsTous.size}) : ${fmtList(communsTous)}`, "tl-success");
            scrollback.print(`-> Spécifiques Président 1 (${specifiquesP1.size}) : ${fmtList(specifiquesP1)}`, "tl-success");
            scrollback.print(`-> Spécifiques Président 2 (${specifiquesP2.size}) : ${fmtList(specifiquesP2)}`, "tl-success");
            scrollback.print(`-> Spécifiques Président 3 (${specifiquesP3.size}) : ${fmtList(specifiquesP3)}`, "tl-success");
            scrollback.print(`-> Partagés P1 ∩ P2 (hors P3) (${partagesP1P2.size}) : ${fmtList(partagesP1P2)}`, "tl-success");
            scrollback.print(`-> Partagés P2 ∩ P3 (hors P1) (${partagesP2P3.size}) : ${fmtList(partagesP2P3)}`, "tl-success");
            scrollback.print(`-> Partagés P1 ∩ P3 (hors P2) (${partagesP1P3.size}) : ${fmtList(partagesP1P3)}`, "tl-success");
            scrollback.print("", "");

            const resultats = {
                metadonnees: {
                    description: "Comparaison automatique des top keywords à partir de fichiers XLSX",
                    total_distinct_p1: kw1.size,
                    total_distinct_p2: kw2.size,
                    total_distinct_p3: kw3.size
                },
                communs_aux_trois: [...communsTous].sort(),
                specifiques_president_1: [...specifiquesP1].sort(),
                specifiques_president_2: [...specifiquesP2].sort(),
                specifiques_president_3: [...specifiquesP3].sort(),
                partages_exclusifs_p1_p2: [...partagesP1P2].sort(),
                partages_exclusifs_p2_p3: [...partagesP2P3].sort(),
                partages_exclusifs_p1_p3: [...partagesP1P3].sort()
            };

            appendDownloadLine(
                "Export JSON prêt",
                "comparaison_keywords_presidents.json",
                JSON.stringify(resultats, null, 4)
            );
        } catch (err) {
            scrollback.print(`[ERROR] ${err.message}`, "tl-error");
        }
    }

    registerTerminalScript({
        id: "keywords-compare",
        pill: "keywords_compare.js",
        command: "./keywords_compare.py --xlsx-compare",
        ready: true,
        intro: [
            { text: "Portage JS de keywords-compare.py — comparaison de 3 listes de keywords (.xlsx).", cls: "tl-comment" },
            { text: "Chargez les 3 fichiers, indiquez le nom de la colonne, puis exécutez.", cls: "tl-comment" }
        ],
        renderForm,
        run
    });
})();
