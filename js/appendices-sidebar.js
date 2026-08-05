/**
 * appendices-sidebar.js
 * -----------------------------------------------------------------
 * Charge le composant appendices-sidebar.html dans le placeholder
 * #sidebar-placeholder (même logique que header/footer), puis marque
 * l'entrée correspondant à la page courante comme active et anime
 * la ligne de progression.
 *
 * Usage, dans chaque page d'annexe :
 *   <link rel="stylesheet" href="css/appendices-sidebar.css">
 *   ...
 *   <div id="sidebar-placeholder"></div>
 *   ...
 *   <script src="js/appendices-sidebar.js" defer></script>
 *
 * Nécessite d'être servi via http(s) (un simple double-clic sur le
 * fichier .html ne permet pas le fetch() d'un fichier local).
 */

(function () {
    const COMPONENT_PATH = "appendices-sidebar.html";

    function currentFileName() {
        const path = window.location.pathname.split("/").pop();
        return path || "appendices-landing.html";
    }

    function positionLines() {
        const track = document.querySelector(".appendix-rail .rail-track");
        const dots = Array.from(document.querySelectorAll(".appendix-rail .rail-dot"));
        const lineBg = document.querySelector(".appendix-rail .rail-line-bg");
        const lineProgress = document.querySelector(".appendix-rail .rail-line-progress");
        if (!track || !lineBg || !lineProgress || dots.length < 2) return;

        const trackTop = track.getBoundingClientRect().top;
        const centerOf = (el) => {
            const r = el.getBoundingClientRect();
            return r.top + r.height / 2 - trackTop;
        };

        const firstCenter = centerOf(dots[0]);
        const lastCenter = centerOf(dots[dots.length - 1]);

        lineBg.style.top = `${firstCenter}px`;
        lineBg.style.height = `${lastCenter - firstCenter}px`;
        lineProgress.style.top = `${firstCenter}px`;

        const activeDot = document.querySelector(".appendix-rail .rail-item.is-active .rail-dot");
        if (activeDot) {
            const activeCenter = centerOf(activeDot);
            requestAnimationFrame(() => {
                lineProgress.style.height = `${activeCenter - firstCenter}px`;
            });
        }
    }

    function activateCurrentItem() {
        const current = currentFileName();
        const items = Array.from(document.querySelectorAll(".appendix-rail .rail-item"));
        const activeIndex = items.findIndex(el => el.dataset.page === current);

        items.forEach((el, i) => {
            const isActive = i === activeIndex;
            el.classList.toggle("is-active", isActive);
            if (isActive) {
                el.setAttribute("aria-current", "page");
            } else {
                el.removeAttribute("aria-current");
            }
        });

        positionLines();
        // recalcule une fois les polices chargées (leur métrique peut légèrement
        // changer la hauteur des lignes de texte, donc le centre des points)
        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(positionLines);
        }
    }

    async function init() {
        const placeholder = document.getElementById("sidebar-placeholder");
        if (!placeholder) {
            console.warn("[appendices-sidebar] #sidebar-placeholder introuvable dans la page.");
            return;
        }

        try {
            const res = await fetch(COMPONENT_PATH);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            placeholder.outerHTML = await res.text();
        } catch (err) {
            console.error("[appendices-sidebar] Impossible de charger le composant :", err);
            return;
        }

        activateCurrentItem();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();