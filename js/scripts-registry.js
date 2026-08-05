/**
 * scripts-registry.js
 * -----------------------------------------------------------------
 * Registre partagé des scripts exécutables dans le terminal.
 *
 * Chaque fichier dans js/scripts/*.js pousse un ou plusieurs objets
 * dans `window.terminalScripts` via `registerTerminalScript(...)`.
 * Ce fichier doit être chargé EN PREMIER (avant terminal-engine.js
 * et avant tous les fichiers js/scripts/*.js).
 *
 * Format attendu pour chaque script :
 * {
 *   id: "identifiant-unique",         // utilisé en interne
 *   pill: "nom_affiche.js",           // libellé du bouton dans le terminal
 *   command: "./nom_affiche.js ...",  // commande "fictive" affichée dans la barre de titre
 *   ready: true,                      // false = affiché grisé/verrouillé (pas encore porté)
 *   intro: [                          // lignes affichées à l'activation du script
 *     { text: "...", cls: "tl-comment" }
 *   ],
 *   renderForm() { return "...HTML..."; },   // construit le formulaire de saisie
 *   async run(scrollback) { ... }            // exécute le calcul et affiche le résultat
 * }
 */

window.terminalScripts = window.terminalScripts || [];

function registerTerminalScript(scriptDef) {
    if (window.terminalScripts.some(s => s.id === scriptDef.id)) {
        console.warn(`[scripts-registry] Un script avec l'id "${scriptDef.id}" existe déjà — ignoré.`);
        return;
    }
    window.terminalScripts.push(scriptDef);
}
