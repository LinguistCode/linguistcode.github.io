/**
 * cochran.js
 * -----------------------------------------------------------------
 * Portage JS de cochran.py — calcul de la taille d'échantillon requise
 * (formule de Cochran, avec correction pour population finie).
 * Purement arithmétique, aucune dépendance externe : portage 1:1.
 */

(function () {
    // Mêmes valeurs par défaut que le script Python (issues de la thèse)
    const DEFAULTS = {
        N: 9958,
        Z: 1.96,
        p: 0.5,
        e: 0.05
    };

    function renderForm() {
        return `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div class="input-group">
                <label class="text-xs mb-1 block opacity-80">> Taille totale de la population (N)</label>
                <input type="number" id="ck-N" class="terminal-input" placeholder="${DEFAULTS.N}" value="${DEFAULTS.N}">
            </div>
            <div class="input-group">
                <label class="text-xs mb-1 block opacity-80">> Écart-réduit (Z) — 1.96 pour 95%</label>
                <input type="number" id="ck-Z" class="terminal-input" step="0.01" placeholder="${DEFAULTS.Z}" value="${DEFAULTS.Z}">
            </div>
            <div class="input-group">
                <label class="text-xs mb-1 block opacity-80">> Proportion présumée (p) — 0.5 = variance max</label>
                <input type="number" id="ck-p" class="terminal-input" step="0.01" min="0" max="1" placeholder="${DEFAULTS.p}" value="${DEFAULTS.p}">
            </div>
            <div class="input-group">
                <label class="text-xs mb-1 block opacity-80">> Marge d'erreur tolérée (e) — 0.05 = 5%</label>
                <input type="number" id="ck-e" class="terminal-input" step="0.01" placeholder="${DEFAULTS.e}" value="${DEFAULTS.e}">
            </div>
        </div>
        <button id="run-btn" class="terminal-btn w-full">EXECUTE --cochran-sample-size</button>`;
    }

    async function run(scrollback) {
        const N = parseFloat(document.getElementById("ck-N").value);
        const Z = parseFloat(document.getElementById("ck-Z").value);
        const p = parseFloat(document.getElementById("ck-p").value);
        const e = parseFloat(document.getElementById("ck-e").value);

        if ([N, Z, p, e].some(isNaN)) {
            scrollback.print("[ERROR] Veuillez entrer des valeurs numériques valides pour N, Z, p et e.", "tl-error");
            return;
        }

        if (p < 0 || p > 1) {
            scrollback.print("[ERROR] La proportion présumée (p) doit être comprise entre 0 et 1.", "tl-error");
            return;
        }

        if (e <= 0) {
            scrollback.print("[ERROR] La marge d'erreur (e) doit être strictement positive.", "tl-error");
            return;
        }

        const q = 1 - p;

        await scrollback.thinking("calcul de l'échantillon théorique (n₀)");

        // n0 = (Z^2 * p * q) / e^2
        const n0 = (Math.pow(Z, 2) * p * q) / Math.pow(e, 2);

        // n = n0 / (1 + (n0 - 1) / N)
        const nFinal = n0 / (1 + (n0 - 1) / N);

        scrollback.print("", "");
        scrollback.print("[RÉSULTATS]", "tl-highlight");
        scrollback.print(`• Variance maximale estimée (p×q)         : ${(p * q).toFixed(4)}`, "tl-info");
        scrollback.print(`• Échantillon théorique brut (n₀)         : ${n0.toFixed(4)} lignes`, "tl-info");
        scrollback.print(`• Échantillon minimal requis réajusté (n) : ${nFinal.toFixed(2)} lignes`, "tl-success");
        scrollback.print(`• Taille à retenir (arrondi supérieur)    : ${Math.ceil(nFinal)} lignes`, "tl-success");
    }

    registerTerminalScript({
        id: "cochran",
        pill: "cochran.js",
        command: "./cochran.py",
        ready: true,
        intro: [
            { text: "Portage JS de cochran.py — taille d'échantillon requise (formule de Cochran, correction population finie).", cls: "tl-comment" },
            { text: "Valeurs par défaut pré-remplies d'après la méthodologie de la thèse (N=9958, Z=1.96, p=0.5, e=0.05).", cls: "tl-comment" }
        ],
        renderForm,
        run
    });
})();
