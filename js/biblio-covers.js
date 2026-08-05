/**
 * book-covers.js
 * -----------------------------------------------------------------
 * Génère des couvertures de livre factices, déterministes (même
 * citekey -> toujours la même couleur), à partir de bibliography.json
 * (produit par build-bibliography.py). Si une entrée a un cover_url,
 * l'image réelle est utilisée à la place.
 *
 * Usage :
 *   <link rel="stylesheet" href="css/book-covers.css">
 *   <div id="bibliography-shelf"></div>
 *   <script src="js/book-covers.js"></script>
 *   <script>BookCovers.init("#bibliography-shelf", "./data/bibliography.json");</script>
 */

(function () {
    // Palette de reliures (toile de bibliothèque désaturée) : [couleur de base, ombre]
    const SPINE_PALETTE = [
        ["#6b2b32", "#411a1f"], // oxblood
        ["#274b3f", "#152e26"], // vert forêt
        ["#22344f", "#141f30"], // marine
        ["#6b4f22", "#403014"], // ocre/moutarde
        ["#402a4a", "#26192c"], // prune
        ["#24474d", "#152b2f"], // sarcelle
    ];

    // Hash déterministe simple (djb2) — même citekey => même résultat, toujours.
    function hashString(str) {
        let hash = 5381;
        for (let i = 0; i < str.length; i++) {
            hash = ((hash << 5) + hash + str.charCodeAt(i)) >>> 0;
        }
        return hash;
    }

    function pickSpine(citekey) {
        const hash = hashString(citekey || "sans-citekey");
        const [base, shade] = SPINE_PALETTE[hash % SPINE_PALETTE.length];
        // légère variation de luminosité pour éviter les doublons trop identiques
        const jitter = 0.9 + ((hash >> 8) % 20) / 100; // 0.90 - 1.09
        return { base, shade, jitter };
    }

    function titleFontSize(title) {
        const len = (title || "").length;
        if (len > 70) return "12px";
        if (len > 45) return "14px";
        if (len > 25) return "16px";
        return "19px";
    }

    function formatAuthors(authors) {
        if (!authors || authors.length === 0) return "";
        if (authors.length === 1) return authors[0];
        if (authors.length === 2) return `${authors[0]} & ${authors[1]}`;
        return `${authors[0]} et al.`;
    }

    function authorSurname(fullName) {
        if (!fullName) return "";
        const parts = fullName.trim().split(/\s+/);
        return parts[parts.length - 1];
    }

    function buildGeneratedCover(entry) {
        const { base, shade, jitter } = pickSpine(entry.citekey);
        const cover = document.createElement("div");
        cover.className = "book-cover is-generated";
        cover.style.setProperty("--bc-base", base);
        cover.style.setProperty("--bc-shade", shade);
        cover.style.setProperty("--bc-jitter", jitter.toFixed(2));

        const title = document.createElement("p");
        title.className = "book-cover-title";
        title.style.fontSize = titleFontSize(entry.title);
        title.textContent = entry.title || "Sans titre";

        const rule = document.createElement("div");
        rule.className = "book-cover-rule";

        const meta = document.createElement("p");
        meta.className = "book-cover-meta";
        const surnames = (entry.authors || []).map(authorSurname).join(", ");
        meta.textContent = [surnames, entry.pub_year].filter(Boolean).join(" · ");

        cover.append(title, rule, meta);
        return cover;
    }

    function buildRealCover(entry) {
        const cover = document.createElement("div");
        cover.className = "book-cover is-real";
        const img = document.createElement("img");
        img.src = entry.cover_url;
        img.alt = `Couverture : ${entry.title || ""}`;
        img.loading = "lazy";
        // si l'image casse, on retombe sur la génération automatique
        img.onerror = () => {
            const fallback = buildGeneratedCover(entry);
            cover.replaceWith(fallback);
        };
        cover.appendChild(img);
        return cover;
    }

    function buildCover(entry) {
        return entry.cover_url ? buildRealCover(entry) : buildGeneratedCover(entry);
    }

    function renderCard(entry, options) {
        const opts = options || {};
        const card = document.createElement("div");
        card.className = "book-card";

        const cover = buildCover(entry);
        card.appendChild(cover);

        const captionTitle = document.createElement("p");
        captionTitle.className = "book-caption-title";
        captionTitle.textContent = entry.title || "";

        const captionMeta = document.createElement("p");
        captionMeta.className = "book-caption-meta";
        captionMeta.textContent = [formatAuthors(entry.authors), entry.pub_year].filter(Boolean).join(" — ");

        card.append(captionTitle, captionMeta);

        if (typeof opts.onSelect === "function") {
            card.setAttribute("role", "button");
            card.setAttribute("tabindex", "0");
            card.classList.add("is-selectable");
            card.addEventListener("click", () => opts.onSelect(entry));
            card.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    opts.onSelect(entry);
                }
            });
        }

        return card;
    }

    async function fetchEntries(jsonPath) {
        const res = await fetch(jsonPath);
        return res.json();
    }

    async function init(containerSelector, jsonPath, options) {
        const opts = options || {};
        const container = document.querySelector(containerSelector);
        if (!container) {
            console.warn(`[book-covers] Conteneur introuvable : ${containerSelector}`);
            return;
        }
        container.classList.add("book-shelf");

        let entries;
        try {
            entries = await fetchEntries(jsonPath);
        } catch (err) {
            console.error("[book-covers] Impossible de charger la bibliographie :", err);
            return;
        }

        container.innerHTML = "";
        entries.forEach(entry => container.appendChild(renderCard(entry, opts)));
        return entries;
    }

    window.BookCovers = { init, renderCard, buildCover, fetchEntries };
})();