/**--scripts-helpers.js--
 * -------------------------------------------------------------
 * Utilitaires partagés par les scripts du terminal (js/scripts/*.js).
 * À charger juste APRÈS scripts-registry.js et AVANT les scripts.
 *
 * Contenu :
 *   - lecture de fichiers (UTF-8 strict ou tolérant, comme Python)
 *   - formatage des nombres à la manière de Python (f"{x:.2f}", f"{x:,}"...)
 *   - ordre de parcours des dossiers façon os.walk / glob sous Windows
 *   - lignes de téléchargement dans le terminal
 *   - statistiques : moyenne, écart-type, percentiles (numpy),
 *     lois F et de l'étendue studentisée (scipy.stats) 
 * -------------------------------------------------------------
 */

(function () {
    const TH = {};

    // ================================================================
    // Divers
    // ================================================================
    TH.sleep = (ms) => new Promise(r => setTimeout(r, ms));

    // Laisse le navigateur respirer pendant les longues boucles
    TH.yieldToBrowser = () => new Promise(r => setTimeout(r, 0));

    const loadedScripts = {};
    TH.loadScriptOnce = function (url, globalName) {
        if (globalName && window[globalName]) return Promise.resolve();
        if (loadedScripts[url]) return loadedScripts[url];
        loadedScripts[url] = new Promise((resolve, reject) => {
            const s = document.createElement("script");
            s.src = url;
            s.onload = () => resolve();
            s.onerror = () => reject(new Error(`Impossible de charger ${url}`));
            document.head.appendChild(s);
        });
        return loadedScripts[url];
    };

    TH.SHEETJS_URL = "https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js";
    TH.JSZIP_URL = "https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js";

    TH.escapeHtml = (s) => String(s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;").replace(/'/g, "&#039;");

    // ================================================================
    // Lecture de fichiers
    // ================================================================

    // mode "strict"  -> équivaut à open(..., encoding='utf-8') : lève une
    //                   erreur (UnicodeDecodeError) si le fichier n'est pas en UTF-8.
    // mode "ignore"  -> équivaut à errors='ignore' : octets invalides supprimés.
    // La BOM éventuelle est conservée, comme en Python avec 'utf-8'.
    TH.readText = async function (file, mode = "strict") {
        const buf = await file.arrayBuffer();
        if (mode === "strict") {
            const dec = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true });
            try {
                return dec.decode(buf);
            } catch (e) {
                const err = new Error(`UnicodeDecodeError : ${file.name}`);
                err.isDecodeError = true;
                throw err;
            }
        }
        const dec = new TextDecoder("utf-8", { fatal: false, ignoreBOM: true });
        return dec.decode(buf).replace(/\uFFFD/g, "");
    };

    // Lecture en mode texte Python : \r\n et \r deviennent \n
    TH.universalNewlines = (text) => text.replace(/\r\n?/g, "\n");

    // Équivalent de f.readlines() (chaque ligne garde son \n final)
    TH.readlines = (text) => TH.universalNewlines(text).match(/[^\n]*\n|[^\n]+$/g) || [];

    // Nom de fichier -> extension .txt (insensible à la casse, comme sous Windows)
    TH.isTxt = (file) => /\.txt$/i.test(file.name);

    // Chemin relatif d'un fichier choisi via <input webkitdirectory>
    TH.relPath = (file) => file.webkitRelativePath || file.name;

    // Nom du dossier racine sélectionné
    TH.rootFolderName = (files) => {
        if (!files || files.length === 0) return "";
        const p = TH.relPath(files[0]);
        return p.includes("/") ? p.split("/")[0] : "";
    };

    // Comparaison "à la NTFS" (ordre renvoyé par os.listdir / glob sous Windows)
    const ntfsCompare = (a, b) => {
        const A = a.toUpperCase(), B = b.toUpperCase();
        if (A < B) return -1;
        if (A > B) return 1;
        return a < b ? -1 : a > b ? 1 : 0;
    };
    TH.ntfsCompare = ntfsCompare;

    // Reproduit l'ordre de os.walk(dossier) (parcours descendant) :
    // à chaque niveau, les fichiers du dossier d'abord, puis chaque sous-dossier
    // récursivement, dans l'ordre NTFS.
    TH.walkOrder = function (files) {
        const root = { files: [], dirs: new Map() };
        for (const f of files) {
            const parts = TH.relPath(f).split("/");
            parts.shift(); // retire le dossier racine sélectionné
            let node = root;
            for (let i = 0; i < parts.length - 1; i++) {
                if (!node.dirs.has(parts[i])) node.dirs.set(parts[i], { files: [], dirs: new Map() });
                node = node.dirs.get(parts[i]);
            }
            node.files.push(f);
        }
        const out = [];
        (function visit(node) {
            node.files.sort((x, y) => ntfsCompare(x.name, y.name)).forEach(f => out.push(f));
            [...node.dirs.keys()].sort(ntfsCompare).forEach(k => visit(node.dirs.get(k)));
        })(root);
        return out;
    };

    // Fichiers situés directement dans le dossier choisi (glob non récursif)
    TH.topLevelOnly = (files) => files.filter(f => TH.relPath(f).split("/").length <= 2);

    // ================================================================
    // Formatage des nombres à la manière de Python
    // ================================================================

    // f"{x:.{d}f}" — arrondi au pair sur la valeur binaire exacte (comme Python),
    // là où toFixed() arrondit les égalités exactes vers le haut.
    TH.pyFixed = function (x, d) {
        if (!isFinite(x)) return isNaN(x) ? "nan" : (x > 0 ? "inf" : "-inf");
        if (Math.abs(x) >= 1e21) return x.toFixed(d);
        const neg = x < 0 || Object.is(x, -0);
        const full = Math.abs(x).toFixed(100); // développement décimal exact (tronqué à 100 chiffres)
        let [intPart, frac] = full.split(".");
        const keep = frac.slice(0, d);
        const rest = frac.slice(d);
        let digits = (intPart + keep).split("").map(Number);
        const first = rest.length ? Number(rest[0]) : 0;
        const tail = rest.slice(1).replace(/0+$/, "");
        let roundUp = false;
        if (first > 5) roundUp = true;
        else if (first === 5) {
            if (tail.length > 0) roundUp = true;
            else roundUp = (digits[digits.length - 1] % 2) === 1; // égalité exacte -> au pair
        }
        if (roundUp) {
            let i = digits.length - 1;
            while (i >= 0) {
                if (digits[i] === 9) { digits[i] = 0; i--; }
                else { digits[i]++; break; }
            }
            if (i < 0) digits.unshift(1);
        }
        const s = digits.join("");
        const ip = s.slice(0, s.length - d) || "0";
        const fp = s.slice(s.length - d);
        const body = d > 0 ? `${ip}.${fp}` : ip;
        const isZero = /^[0.]+$/.test(body);
        return (neg && !isZero ? "-" : (neg && isZero ? "-" : "")) + body;
    };

    // f"{x:.{d}e}" — exposant sur 2 chiffres minimum, signé (1.2345e-05)
    TH.pyExp = function (x, d) {
        if (!isFinite(x)) return isNaN(x) ? "nan" : (x > 0 ? "inf" : "-inf");
        const s = x.toExponential(d);
        return s.replace(/e([+-])(\d)$/, "e$10$2");
    };

    // f"{x:+.3f}"
    TH.pySignedFixed = (x, d) => (x >= 0 ? "+" : "") + TH.pyFixed(x, d);

    // f"{n:,}" puis .replace(',', ' ') dans les scripts
    TH.pyThousands = (n, sep = ",") => {
        const s = String(Math.trunc(Math.abs(n)));
        const out = s.replace(/\B(?=(\d{3})+(?!\d))/g, sep);
        return (n < 0 ? "-" : "") + out;
    };

    // str(float) en Python (repr le plus court)
    TH.pyFloatRepr = function (x) {
        if (isNaN(x)) return "nan";
        if (!isFinite(x)) return x > 0 ? "inf" : "-inf";
        const a = Math.abs(x);
        if (a !== 0 && (a < 1e-4 || a >= 1e16)) {
            return x.toExponential().replace(/e([+-])(\d)$/, "e$10$2");
        }
        if (Number.isInteger(x)) return x.toFixed(1);
        return String(x);
    };

    // Python round(x, n) : arrondi au pair sur la valeur exacte
    TH.pyRound = (x, n) => Number(TH.pyFixed(x, n));

    // str.ljust / f"{s:<n}"
    TH.ljust = (s, n) => String(s).padEnd(n, " ");
    TH.rjust = (s, n) => String(s).padStart(n, " ");

    // Tri Python sur des chaînes (ordre des points de code)
    TH.cmpCodePoints = (a, b) => {
        const A = Array.from(a), B = Array.from(b);
        const n = Math.min(A.length, B.length);
        for (let i = 0; i < n; i++) {
            const ca = A[i].codePointAt(0), cb = B[i].codePointAt(0);
            if (ca !== cb) return ca - cb;
        }
        return A.length - B.length;
    };

    // ================================================================
    // Téléchargements
    // ================================================================
    TH.appendDownloadLine = function (label, filename, blob) {
        const container = document.getElementById("terminal-scrollback");
        const url = URL.createObjectURL(blob);
        const line = document.createElement("div");
        line.className = "tl-line tl-success";
        line.innerHTML = `-> ${TH.escapeHtml(label)} : <a href="${url}" download="${TH.escapeHtml(filename)}" style="color:#58a6ff;text-decoration:underline;">${TH.escapeHtml(filename)}</a>`;
        container.appendChild(line);
        container.scrollTop = container.scrollHeight;
    };

    // json.dump(obj, f, indent=4, ensure_ascii=False)
    TH.pyJsonDump = (obj) => JSON.stringify(obj, null, 4);

    // ================================================================
    // Statistiques descriptives (conventions numpy)
    // ================================================================
    TH.mean = (arr) => arr.reduce((s, v) => s + v, 0) / arr.length;

    // np.std (ddof=0) ; ddof=1 pour la variance d'échantillon
    TH.variance = (arr, ddof = 0) => {
        const m = TH.mean(arr);
        return arr.reduce((s, v) => s + (v - m) * (v - m), 0) / (arr.length - ddof);
    };
    TH.std = (arr, ddof = 0) => Math.sqrt(TH.variance(arr, ddof));

    // np.percentile (méthode "linear" par défaut)
    TH.percentile = (arr, p) => {
        const s = Float64Array.from(arr).sort();
        const idx = (p / 100) * (s.length - 1);
        const lo = Math.floor(idx), hi = Math.ceil(idx);
        return s[lo] + (s[hi] - s[lo]) * (idx - lo);
    };

    // ================================================================
    // Fonctions spéciales
    // ================================================================
    // log Gamma (Lanczos, g=7, n=9) — précision ~1e-15
    const LANCZOS = [0.99999999999980993, 676.5203681218851, -1259.1392167224028,
        771.32342877765313, -176.61502916214059, 12.507343278686905,
        -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];
    TH.lgamma = function lgamma(z) {
        if (z < 0.5) return Math.log(Math.PI / Math.abs(Math.sin(Math.PI * z))) - lgamma(1 - z);
        z -= 1;
        let x = LANCZOS[0];
        for (let i = 1; i < 9; i++) x += LANCZOS[i] / (z + i);
        const t = z + 7.5;
        return 0.5 * Math.log(2 * Math.PI) + (z + 0.5) * Math.log(t) - t + Math.log(x);
    };

    // Fraction continue de la bêta incomplète (Numerical Recipes, betacf)
    function betacf(a, b, x) {
        const MAXIT = 500, EPS = 1e-15, FPMIN = 1e-300;
        const qab = a + b, qap = a + 1, qam = a - 1;
        let c = 1, d = 1 - qab * x / qap;
        if (Math.abs(d) < FPMIN) d = FPMIN;
        d = 1 / d;
        let h = d;
        for (let m = 1; m <= MAXIT; m++) {
            const m2 = 2 * m;
            let aa = m * (b - m) * x / ((qam + m2) * (a + m2));
            d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
            c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
            d = 1 / d; h *= d * c;
            aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2));
            d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
            c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
            d = 1 / d;
            const del = d * c;
            h *= del;
            if (Math.abs(del - 1) < EPS) break;
        }
        return h;
    }

    // Bêta incomplète régularisée I_x(a, b)
    TH.betaInc = function (x, a, b) {
        if (x <= 0) return 0;
        if (x >= 1) return 1;
        const lbt = TH.lgamma(a + b) - TH.lgamma(a) - TH.lgamma(b) + a * Math.log(x) + b * Math.log(1 - x);
        if (x < (a + 1) / (a + b + 2)) return Math.exp(lbt) * betacf(a, b, x) / a;
        return 1 - Math.exp(lbt) * betacf(b, a, 1 - x) / b;
    };

    // scipy.stats.f.sf(F, dfn, dfd)
    TH.fSf = function (F, dfn, dfd) {
        if (isNaN(F)) return NaN;
        if (F <= 0) return 1;
        if (!isFinite(F)) return 0;
        return TH.betaInc(dfd / (dfd + dfn * F), dfd / 2, dfn / 2);
    };

    // Fonction de répartition de la loi normale centrée réduite
    function erfc(x) {
        const z = Math.abs(x);
        const t = 1 / (1 + 0.5 * z);
        const r = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 +
            t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 +
                t * (-0.82215223 + t * 0.17087277)))))))));
        return x >= 0 ? r : 2 - r;
    }
    // Φ(x) précis (algorithme de Cody via développement W. J. Cody / Hart) :
    // on utilise l'identité Φ(x) = 0.5 * erfc(-x / √2) avec un erfc de haute précision.
    function erfcPrecise(x) {
        // Chebyshev-free high precision erfc (W. J. Cody 1969 rational approximations)
        const ax = Math.abs(x);
        let r;
        if (ax < 0.5) {
            const t = x * x;
            const p = [3.20937758913846947e03, 3.77485237685302021e02, 1.13864154151050156e02, 3.16112374387056560e00, 1.85777706184603153e-1];
            const q = [2.84423683343917062e03, 1.28261652607737228e03, 2.44024637934444173e02, 2.36012909523441209e01, 1.0];
            const num = (((p[4] * t + p[3]) * t + p[2]) * t + p[1]) * t + p[0];
            const den = (((q[4] * t + q[3]) * t + q[2]) * t + q[1]) * t + q[0];
            return 1 - x * num / den;
        } else if (ax < 4) {
            const p = [1.23033935479799725e03, 2.05107837782607147e03, 1.71204761263407058e03, 8.81952221241769090e02,
                2.98635138197400131e02, 6.61191906371416295e01, 8.88314979438837594e00, 5.64188496988670089e-1, 2.15311535474403846e-8];
            const q = [1.23033935480374942e03, 3.43936767414372164e03, 4.36261909014324716e03, 3.29079923573345963e03,
                1.62138957456669019e03, 5.37181101862009858e02, 1.17693950891312499e02, 1.57449261107098347e01, 1.0];
            let num = p[8], den = q[8];
            for (let i = 7; i >= 0; i--) { num = num * ax + p[i]; den = den * ax + q[i]; }
            r = Math.exp(-ax * ax) * num / den;
        } else {
            const p = [-6.58749161529837803e-4, -1.60837851487422766e-2, -1.25781726111229246e-1, -3.60344899949804439e-1,
            -3.05326634961232344e-1, -1.63153871373020978e-2];
            const q = [2.33520497626869185e-3, 6.05183413124413191e-2, 5.27905102951428412e-1, 1.87295284992346725e00,
                2.56852019228982242e00, 1.0];
            const z = 1 / (ax * ax);
            let num = p[5], den = q[5];
            for (let i = 4; i >= 0; i--) { num = num * z + p[i]; den = den * z + q[i]; }
            r = Math.exp(-ax * ax) / ax * (0.5641895835477563 + z * num / den);
        }
        return x >= 0 ? r : 2 - r;
    }
    TH.erfcApprox = erfc;
    TH.erfc = erfcPrecise;
    const pnorm = (x, mu = 0) => 0.5 * erfcPrecise(-(x - mu) / Math.SQRT2);

    // scipy.stats.chi2.sf(x, 1) = erfc(√(x/2))
    TH.chi2SfDf1 = (x) => (x <= 0 ? 1 : erfcPrecise(Math.sqrt(x / 2)));

    // ---------------- Loi de l'étendue studentisée ----------------
    // Portage de ptukey()/wprob() de R (Copenhaver & Holland 1988, AS 190),
    // utilisé pour le test post-hoc de Tukey (scipy.stats.studentized_range).
    function wprob(w, rr, cc) {
        const nleg = 12, ihalf = 6;
        const C1 = -30, C2 = -50, C3 = 60, bb = 8, wlar = 3, wincr1 = 2, wincr2 = 3;
        const xleg = [0.981560634246719250690549090149, 0.904117256370474856678465866119,
            0.769902674194304687036893833213, 0.587317954286617447296702418941,
            0.367831498998180193752691536644, 0.125233408511468915472441369464];
        const aleg = [0.047175336386511827194615961485, 0.106939325995318430960254718194,
            0.160078328543346226334652529543, 0.203167426723065921749064455810,
            0.233492536538354808760849898925, 0.249147045813402785000562436043];
        const qsqz = w * 0.5;
        if (qsqz >= bb) return 1.0;
        let pr_w = 2 * pnorm(qsqz) - 1;
        if (pr_w >= 1) pr_w = 1; else pr_w = Math.pow(pr_w, cc);
        const wincr = w > wlar ? wincr1 : wincr2;
        let blb = qsqz;
        const binc = (bb - qsqz) / wincr;
        let bub = blb + binc;
        let einsum = 0;
        const cc1 = cc - 1;
        for (let wi = 1; wi <= wincr; wi++) {
            let elsum = 0;
            const a = 0.5 * (bub + blb);
            const b = 0.5 * (bub - blb);
            for (let jj = 1; jj <= nleg; jj++) {
                let j, xx;
                if (ihalf < jj) { j = (nleg - jj) + 1; xx = xleg[j - 1]; }
                else { j = jj; xx = -xleg[j - 1]; }
                const c = b * xx;
                const ac = a + c;
                const qexpo = ac * ac;
                if (qexpo > C3) break;
                const pplus = 2 * pnorm(ac);
                const pminus = 2 * pnorm(ac, w);
                let rinsum = (pplus * 0.5) - (pminus * 0.5);
                if (rinsum >= Math.exp(C1 / cc1)) {
                    rinsum = (aleg[j - 1] * Math.exp(-(0.5 * qexpo))) * Math.pow(rinsum, cc1);
                    elsum += rinsum;
                }
            }
            elsum *= ((2.0 * b) * cc) / Math.sqrt(2 * Math.PI);
            einsum += elsum;
            blb = bub;
            bub += binc;
        }
        pr_w += einsum;
        if (pr_w <= Math.exp(C1 / rr)) return 0;
        pr_w = Math.pow(pr_w, rr);
        if (pr_w >= 1) return 1;
        return pr_w;
    }

    // P(Q <= q) pour k groupes (cc) et df degrés de liberté
    TH.ptukey = function (q, cc, df, rr = 1) {
        if (q <= 0) return 0;
        if (df < 2 || rr < 1 || cc < 2) return NaN;
        if (!isFinite(q)) return 1;
        const nlegq = 16, ihalfq = 8;
        const eps1 = -30.0, eps2 = 1.0e-14, dhaf = 100.0, dquar = 800.0, deigh = 5000.0, dlarg = 25000.0;
        const ulen1 = 1.0, ulen2 = 0.5, ulen3 = 0.25, ulen4 = 0.125;
        const xlegq = [0.989400934991649932596154173450, 0.944575023073232576077988415535,
            0.865631202387831743880467897712, 0.755404408355003033895101194847,
            0.617876244402643748446671764049, 0.458016777657227386342419442984,
            0.281603550779258913230460501460, 0.950125098376374401853193354250e-1];
        const alegq = [0.271524594117540948517805724560e-1, 0.622535239386478928628438369944e-1,
            0.951585116824927848099251076022e-1, 0.124628971255533872052476282192,
            0.149595988816576732081501730547, 0.169156519395002538189312079030,
            0.182603415044923588866763667969, 0.189450610455068496285396723208];
        if (df > dlarg) return wprob(q, rr, cc);
        const f2 = df * 0.5;
        let f2lf = ((f2 * Math.log(df)) - (df * Math.LN2)) - TH.lgamma(f2);
        const f21 = f2 - 1.0;
        const ff4 = df * 0.25;
        let ulen;
        if (df <= dhaf) ulen = ulen1;
        else if (df <= dquar) ulen = ulen2;
        else if (df <= deigh) ulen = ulen3;
        else ulen = ulen4;
        f2lf += Math.log(ulen);
        let ans = 0.0, otsum = 0.0;
        for (let i = 1; i <= 50; i++) {
            otsum = 0.0;
            const twa1 = (2 * i - 1) * ulen;
            for (let jj = 1; jj <= nlegq; jj++) {
                let j, t1;
                if (ihalfq < jj) {
                    j = jj - ihalfq - 1;
                    t1 = (f2lf + (f21 * Math.log(twa1 + (xlegq[j] * ulen)))) - (((xlegq[j] * ulen) + twa1) * ff4);
                } else {
                    j = jj - 1;
                    t1 = (f2lf + (f21 * Math.log(twa1 - (xlegq[j] * ulen)))) + (((xlegq[j] * ulen) - twa1) * ff4);
                }
                if (t1 >= eps1) {
                    let qsqz;
                    if (ihalfq < jj) qsqz = q * Math.sqrt(((xlegq[j] * ulen) + twa1) * 0.5);
                    else qsqz = q * Math.sqrt(((-(xlegq[j] * ulen)) + twa1) * 0.5);
                    const wprb = wprob(qsqz, rr, cc);
                    otsum += (wprb * alegq[j]) * Math.exp(t1);
                }
            }
            if (i * ulen >= 1.0 && otsum <= eps2) break;
            ans += otsum;
        }
        return ans > 1 ? 1 : ans;
    };

    // Quantile de l'étendue studentisée (inversion de ptukey par dichotomie)
    TH.qtukey = function (p, cc, df) {
        let lo = 0, hi = 1;
        while (TH.ptukey(hi, cc, df) < p) hi *= 2;
        for (let i = 0; i < 100; i++) {
            const mid = 0.5 * (lo + hi);
            if (TH.ptukey(mid, cc, df) < p) lo = mid; else hi = mid;
            if (hi - lo < 1e-10) break;
        }
        return 0.5 * (lo + hi);
    };

    // ================================================================
    // Générateur pseudo-aléatoire à graine (mulberry32)
    // ================================================================
    TH.seededRandom = function (seed) {
        let a = seed >>> 0;
        return function () {
            a = (a + 0x6D2B79F5) >>> 0;
            let t = a;
            t = Math.imul(t ^ (t >>> 15), t | 1);
            t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        };
    };

    window.TH = TH;
})();
