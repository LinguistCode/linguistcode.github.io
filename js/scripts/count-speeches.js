/** -- count-speeches.js --
 * -------------------------------------------------------------
 * compte les fichiers .txt d'un dossier et de tous ses sous-dossiers.
 * Le dossier est lu localement par le navigateur : rien n'est envoyé.
 * -------------------------------------------------------------
 */

(function () {
    function renderForm() {
        return `
        <div class="input-group">
            <label class="text-xs mb-1 block opacity-80">> Dossier à analyser (sous-dossiers inclus)</label>
            <input type="file" id="cs-folder" class="terminal-input" webkitdirectory directory multiple>
        </div>
        <button id="run-btn" class="terminal-btn w-full">EXECUTE --count-txt</button>`;
    }

    async function run(scrollback) {
        const files = Array.from(document.getElementById("cs-folder").files || []);
        if (files.length === 0) {
            scrollback.print("[ERROR] Veuillez sélectionner un dossier.", "tl-error");
            return;
        }
        const folder = TH.rootFolderName(files);
        await scrollback.thinking(`parcours récursif de ${folder || "dossier"}`);
        const total = files.filter(TH.isTxt).length;

        scrollback.print("", "");
        scrollback.print("[RÉSULTATS]", "tl-highlight");
        scrollback.print(`Total .txt files found: ${total}`, "tl-success");
        if (files.length !== total) {
            scrollback.print(`(${files.length - total} autre(s) fichier(s) ignoré(s) : extension différente de .txt)`, "tl-comment");
        }
    }

    registerTerminalScript({
        id: "count-speeches",
        pill: "count_speeches.js",
        command: "./count-speeches.py",
        ready: true,
        intro: [
            { text: "Portage JS de count-speeches.py — nombre de discours (.txt) dans un dossier, sous-dossiers compris.", cls: "tl-comment" },
            { text: "Le dossier est lu localement par votre navigateur : aucun fichier n'est envoyé.", cls: "tl-comment" }
        ],
        renderForm,
        run
    });
})();
