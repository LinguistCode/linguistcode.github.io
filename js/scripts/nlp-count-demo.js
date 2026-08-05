/**
 * nlp-count-demo.js
 * -----------------------------------------------------------------
 * NLP-count.py repose sur spaCy (tokenizer linguistique + modèle
 * en_core_web_sm), qui n'a pas d'équivalent en JavaScript. Un vrai
 * portage donnerait une approximation regex peu fiable et présentée
 * à tort comme équivalente à spaCy.
 *
 * Ce module propose donc une ANIMATION PÉDAGOGIQUE, plus détaillée
 * qu'un simple résumé : chargement du modèle, désactivation des
 * modules inutiles, scan récursif du dossier, traitement fichier par
 * fichier (échantillon réel de noms de fichiers du corpus Trump),
 * progression périodique (calquée sur le script Python d'origine),
 * un mini-exemple pédagogique de tokenisation, puis les résultats
 * RÉELS d'une exécution effective de NLP-count.py sur ce dossier.
 */

(function () {
    // Noms de fichiers réels du corpus (triés chronologiquement)
    const DEMO_FILES = [
        "T - 2017-04-29 - Remarks at a MAGA Rally.txt",
        "T - 2017-12-09 - Remarks at the Opening of the .txt",
        "T - 2018-03-15 - Remarks on Receiving the Shamr.txt",
        "T - 2018-11-28 - Remarks on Lighting the Nation.txt",
        "T - 2019-04-27 - Remarks at a Keep America Grea.txt",
        "T - 2019-07-25 - Remarks at a Swearingin Recept.txt",
        "T - 2019-11-11 - Remarks at a Veterans Day Para.txt",
        "T - 2020-03-09 - Remarks at a White House Coron.txt",
        "T - 2020-06-25 - Remarks at the Fincantieri Mar.txt",
        "T - 2020-08-18 - Remarks at a Make America Grea.txt",
        "T - 2020-09-22 - Remarks at a Make America Grea.txt",
        "T - 2021-01-07 - Videotaped Remarks on the Atta.txt"
    ];

    // Résultats réels d'une exécution effective de NLP-count.py sur ce dossier
    const REAL_OUTPUT = {
        "dossier_analyse": "A:\\myFiles\\Corpus\\Trump",
        "fichiers_traites": 355,
        "total_tokens": 1626297,
        "total_types": 18183,
        "uber_index": 45.5188
    };

    // Phrase d'exemple purement pédagogique (n'entre PAS dans les résultats finaux),
    // pour illustrer concrètement ce que fait le filtre is_alpha de spaCy.
    const TOY_SENTENCE = "Believe me, we've cut taxes by 20% -- and it's working!";

    function sleep(ms) {
        return new Promise(r => setTimeout(r, ms));
    }

    function tokenizeSimple(text) {
        return text.match(/[A-Za-zÀ-ÖØ-öø-ÿ]+(?:'[A-Za-zÀ-ÖØ-öø-ÿ]+)?/g) || [];
    }

    function renderForm() {
        return `
        <p class="text-xs mb-4 opacity-70">
            spaCy n'a pas d'équivalent exécutable en JavaScript côté navigateur. Cette démonstration
            rejoue en détail le déroulé de NLP-count.py — chargement du modèle, scan du dossier,
            traitement fichier par fichier — puis affiche les résultats réels obtenus lors d'une
            exécution effective du script sur ce corpus.
        </p>
        <button id="run-btn" class="terminal-btn w-full">EXECUTE --demo</button>`;
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

    async function run(scrollback) {
        // ---- 1. Chargement du modèle ----
        await scrollback.thinking("chargement du modèle linguistique spaCy (en_core_web_sm)", 1300);
        await scrollback.printTyped("> modèle chargé : pipeline anglais (tok2vec, tagger, lemmatizer, attribute_ruler)", "tl-comment", 16);
        await sleep(300);
        await scrollback.printTyped("> désactivation des modules 'parser' et 'ner' (analyse syntaxique, entités nommées)", "tl-comment", 16);
        await sleep(200);
        await scrollback.printTyped("> ces modules ne sont pas nécessaires : seule la tokenisation nous intéresse ici", "tl-comment", 16);
        await sleep(200);
        await scrollback.printTyped("> nlp.max_length fixé à 2 000 000 caractères (fichiers longs)", "tl-comment", 16);
        await sleep(400);

        // ---- 2. Mini-exemple pédagogique de tokenisation ----
        scrollback.print("", "");
        await scrollback.printTyped("> Exemple pédagogique — ce que fait le filtre token.is_alpha :", "tl-info", 16);
        await sleep(200);
        scrollback.print(`"${TOY_SENTENCE}"`, "tl-comment");
        await sleep(400);
        const toyTokens = tokenizeSimple(TOY_SENTENCE);
        await scrollback.thinking("tokenisation de l'exemple", 700);
        scrollback.print(`-> tokens retenus (is_alpha)  : ${toyTokens.join(", ")}`, "tl-success");
        scrollback.print(`-> éléments exclus (ponctuation, nombres) : ",", "20%", "--", "!"`, "tl-error");
        await sleep(500);

        // ---- 3. Scan du dossier ----
        scrollback.print("", "");
        await scrollback.thinking(`scan récursif du dossier : ${REAL_OUTPUT.dossier_analyse}`, 1000);
        scrollback.print(`-> ${REAL_OUTPUT.fichiers_traites} fichier(s) .txt trouvé(s)`, "tl-info");
        await sleep(300);
        await scrollback.printTyped(`> affichage d'un échantillon représentatif de ${DEMO_FILES.length} fichiers sur ${REAL_OUTPUT.fichiers_traites} :`, "tl-comment", 14);
        await sleep(300);

        // ---- 4. Traitement fichier par fichier (échantillon réel) ----
        for (const filename of DEMO_FILES) {
            await sleep(480);
            scrollback.print(`-> traitement : ${filename}`, "tl-comment");
        }

        await sleep(300);
        scrollback.print("", "");
        await scrollback.printTyped("> ... reste du corpus traité de la même manière ...", "tl-comment", 14);
        await sleep(300);

        // ---- 5. Progression périodique (comme dans le script Python d'origine) ----
        const progressSteps = [50, 100, 150, 200, 250, 300, 350];
        for (const step of progressSteps) {
            await sleep(280);
            scrollback.print(`Progression : ${step} / ${REAL_OUTPUT.fichiers_traites} fichiers analysés...`, "tl-info");
        }
        await sleep(300);
        scrollback.print(`Progression : ${REAL_OUTPUT.fichiers_traites} / ${REAL_OUTPUT.fichiers_traites} fichiers analysés...`, "tl-info");

        // ---- 6. Calcul final ----
        scrollback.print("", "");
        await scrollback.thinking("comptage des tokens/types et calcul de l'Über index", 1200);

        // ---- 7. Résultats réels ----
        scrollback.print("", "");
        scrollback.print("[RÉSULTATS DE L'ANALYSE NLP]", "tl-highlight");
        scrollback.print(`-> Dossier analysé      : ${REAL_OUTPUT.dossier_analyse}`, "tl-success");
        scrollback.print(`-> Fichiers traités     : ${REAL_OUTPUT.fichiers_traites}`, "tl-success");
        scrollback.print(`-> Tokens               : ${REAL_OUTPUT.total_tokens.toLocaleString('fr-FR')}`, "tl-success");
        scrollback.print(`-> Types                : ${REAL_OUTPUT.total_types.toLocaleString('fr-FR')}`, "tl-success");
        scrollback.print(`-> Über Index           : ${REAL_OUTPUT.uber_index}`, "tl-success");
        scrollback.print("", "");
        scrollback.print("[NOTE] Chargement, scan et progression sont animés à titre pédagogique ;", "tl-comment");
        scrollback.print("les résultats ci-dessus proviennent d'une exécution réelle de NLP-count.py.", "tl-comment");

        appendDownloadLine("Export JSON des résultats", "resultats_nlp_trump.json", JSON.stringify(REAL_OUTPUT, null, 4));
    }

    registerTerminalScript({
        id: "nlp-count-demo",
        pill: "NLP_count.js (démo)",
        command: "./NLP-count.py  # démonstration animée",
        ready: true,
        intro: [
            { text: "NLP-count.py utilise spaCy, une bibliothèque Python de NLP sans équivalent JS.", cls: "tl-comment" },
            { text: "Ce module rejoue en détail le déroulé du script en animation, avec des résultats réels.", cls: "tl-comment" }
        ],
        renderForm,
        run
    });
})();