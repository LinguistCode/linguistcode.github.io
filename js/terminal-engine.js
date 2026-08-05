/**
 * terminal-engine.js
 * -----------------------------------------------------------------
 * Moteur générique du terminal animé. Ne connaît RIEN des scripts
 * eux-mêmes : il lit window.terminalScripts (rempli par
 * scripts-registry.js + js/scripts/*.js) et gère :
 *   - la séquence de démarrage animée
 *   - le journal de session ("scrollback") avec effet de frappe
 *   - le sélecteur de scripts (pastilles)
 *   - le branchement du formulaire actif et du bouton d'exécution
 *
 * Pour ajouter un nouveau script : créez un fichier dans js/scripts/,
 * appelez registerTerminalScript({...}) dedans, puis ajoutez
 * <script src="js/scripts/votre-fichier.js"></script> dans le HTML.
 * Ce fichier n'a besoin d'aucune modification.
 */



// ---------- Scrollback controller: handles all "terminal feel" ----------
function createScrollback(el) {
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));

    function scrollToBottom() {
        el.scrollTop = el.scrollHeight;
    }

    function print(text, cls = "tl-info") {
        const line = document.createElement("div");
        line.className = `tl-line ${cls}`;
        line.textContent = text;
        el.appendChild(line);
        scrollToBottom();
        return line;
    }

    // Types out text character-by-character for an authentic terminal feel.
    async function printTyped(text, cls = "tl-info", speed = 10) {
        const line = document.createElement("div");
        line.className = `tl-line ${cls}`;
        el.appendChild(line);
        for (let i = 0; i < text.length; i++) {
            line.textContent += text[i];
            if (i % 2 === 0) scrollToBottom();
            await sleep(speed);
        }
        scrollToBottom();
        return line;
    }

    // Brief animated "..." beat before a result, like a process running.
    async function thinking(label, duration = 650) {
        const line = document.createElement("div");
        line.className = "tl-line tl-comment";
        line.innerHTML = `> ${label}<span class="tl-thinking"><span>.</span><span>.</span><span>.</span></span>`;
        el.appendChild(line);
        scrollToBottom();
        await sleep(duration);
        return line;
    }

    function clear() {
        el.innerHTML = "";
    }

    return { print, printTyped, thinking, clear, scrollToBottom };
}

// ---------- Boot sequence played once on page load ----------
async function playBootSequence(scrollback) {
    const bootLines = [
        { text: "[boot] corpus-analyzer v2.1 — environnement JS (adaptations de scripts Python)", cls: "tl-comment", speed: 6 },
        { text: "[ok] modules chargés : stats, regex, io-sim", cls: "tl-success", speed: 4 },
        { text: "Tapez ou cliquez un script ci-dessous pour l'activer.", cls: "tl-info", speed: 8 }
    ];
    for (const l of bootLines) {
        await scrollback.printTyped(l.text, l.cls, l.speed);
        await new Promise(r => setTimeout(r, 120));
    }
}

// ---------- Wiring: picker, form zone, run button ----------
let activeScript = null;

function renderPicker() {
    const picker = document.getElementById("script-picker");
    const scripts = window.terminalScripts || [];

    picker.innerHTML = scripts.map(s => `
        <button type="button"
            class="script-pill ${s.ready ? '' : 'locked'}"
            data-id="${s.id}"
            title="${s.ready ? '' : 'Portage JS pas encore disponible'}">
            ${s.pill}
        </button>`).join("");

    picker.querySelectorAll(".script-pill").forEach(btn => {
        btn.addEventListener("click", () => activateScript(btn.dataset.id));
    });
}

async function activateScript(id) {
    const scripts = window.terminalScripts || [];
    const script = scripts.find(s => s.id === id);
    if (!script) return;
    activeScript = script;

    // update pill highlighting
    document.querySelectorAll(".script-pill").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.id === id);
    });

    // update window title bar to reflect the "loaded" command
    document.getElementById("window-title-text").textContent =
        `aurelien@corpus-analyzer:~$ ${script.command}`;

    const scrollback = createScrollback(document.getElementById("terminal-scrollback"));
    scrollback.print(`$ ${script.command}`, "tl-prompt");
    for (const line of script.intro) {
        await scrollback.printTyped(line.text, line.cls, 6);
    }

    // render the form
    const formzone = document.getElementById("terminal-formzone");
    formzone.innerHTML = script.renderForm();

    // allow scripts to attach any extra listeners/state after their form is in the DOM
    if (typeof script.onFormReady === "function") {
        script.onFormReady(formzone);
    }

    // Scripts with multiple internal sub-tools (e.g. a submenu) manage their own
    // run-button wiring inside onFormReady and set selfManagesRunButton = true
    // to opt out of this generic binding.
    if (!script.selfManagesRunButton) {
        const runBtn = formzone.querySelector("#run-btn") || formzone.querySelector("button.terminal-btn");
        if (runBtn && !runBtn.disabled) {
            runBtn.addEventListener("click", async () => {
                runBtn.disabled = true;
                const originalLabel = runBtn.textContent;
                runBtn.textContent = "EXECUTING...";
                await script.run(scrollback);
                runBtn.disabled = false;
                runBtn.textContent = originalLabel;
            });
        }
    }
}

// ---------- Restart: triggered by the red "close" window dot ----------
async function restartTerminal() {
    activeScript = null;

    // wipe scrollback + active form
    const scrollback = createScrollback(document.getElementById("terminal-scrollback"));
    scrollback.clear();
    document.getElementById("terminal-formzone").innerHTML = "";

    // reset pill highlighting
    document.querySelectorAll(".script-pill").forEach(btn => btn.classList.remove("active"));

    // reset the window title bar
    document.getElementById("window-title-text").textContent = "aurelien@corpus-analyzer:~$";

    // replay boot sequence, then auto-load the first script again
    await playBootSequence(scrollback);
    const scripts = window.terminalScripts || [];
    const first = scripts.find(s => s.ready) || scripts[0];
    if (first) activateScript(first.id);
}

// ---------- Boot on page load ----------
document.addEventListener("DOMContentLoaded", async () => {
    renderPicker();

    // red dot = clear + restart the terminal
    const closeDot = document.querySelector(".dot.close");
    if (closeDot) {
        closeDot.style.cursor = "pointer";
        closeDot.title = "Effacer et redémarrer le terminal";
        closeDot.addEventListener("click", restartTerminal);
    }

    const scrollback = createScrollback(document.getElementById("terminal-scrollback"));
    await playBootSequence(scrollback);
    // auto-load the first ready script so the terminal isn't empty
    const scripts = window.terminalScripts || [];
    const first = scripts.find(s => s.ready) || scripts[0];
    if (first) activateScript(first.id);
});