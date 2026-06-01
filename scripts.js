document.addEventListener("DOMContentLoaded", () => {
    // 1. Fonction pour charger les composants HTML
    const loadComponent = async (id, file) => {
        const element = document.getElementById(id);
        if (element) {
            try {
                const response = await fetch(file);
                if (response.ok) {
                    element.innerHTML = await response.text();
                }
            } catch (error) {
                console.error(`Erreur lors du chargement de ${file}:`, error);
            }
        }
    };

    // 2. Logique de gestion du lien de navigation actif
    const setActiveLink = () => {
        const path = window.location.pathname;
        let page = path.split("/").pop();
        if (page === "" || page === "index.html") page = "index.html";

        const navLinks = document.querySelectorAll('.nav-link');

        navLinks.forEach(link => {
            const linkPage = link.getAttribute('data-page');

            // On redéfinit complètement les classes en fonction de l'état
            if (linkPage === page) {
                link.className = "nav-link font-['Newsreader'] italic font-medium text-emerald-900 dark:text-emerald-400 border-b-2 border-emerald-900 dark:border-emerald-400 pb-1 translate-y-[1px] transition-transform";
            } else {
                link.className = "nav-link font-['Newsreader'] italic font-medium text-zinc-600 dark:text-zinc-400 hover:text-emerald-800 dark:hover:text-emerald-300 transition-colors";
            }
        });
    };

    // 3. Charger les composants, puis initialiser les scripts
    Promise.all([
        loadComponent('header-placeholder', 'header.html'),
        loadComponent('footer-placeholder', 'footer.html')
    ]).then(() => {
        setActiveLink();
        initMobileMenu();
        initCopyEmail();
        initCommsToggle();
        initMediaCarousel();
    });
});

// Ré-initialisation du menu mobile
function initMobileMenu() {
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const navLinks = document.getElementById('nav-links');
    if (mobileMenuBtn && navLinks) {
        const menuIcon = mobileMenuBtn.querySelector('.material-symbols-outlined');
        mobileMenuBtn.addEventListener('click', () => {
            navLinks.classList.toggle('hidden');
            navLinks.classList.toggle('flex');
            menuIcon.textContent = navLinks.classList.contains('hidden') ? 'menu' : 'close';
        });
    }
}

// Ré-initialisation du bouton de copie d'email
function initCopyEmail() {
    const btn = document.getElementById('copyEmailBtn');
    if (btn) {
        const emailToCopy = 'amet.sorbonne@gmail.com';
        btn.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(emailToCopy);
                const toast = document.createElement('div');
                toast.textContent = 'Email copié !';
                toast.className = 'fixed bottom-6 right-6 bg-emerald-700 text-white text-sm px-4 py-2 rounded shadow-lg z-[100]';
                document.body.appendChild(toast);
                setTimeout(() => toast.remove(), 2200);
            } catch (err) {
                alert('Impossible de copier l\'email. Veuillez le copier manuellement : ' + emailToCopy);
            }
        });
    }
}

// Fonction pour gérer l'affichage de toutes les communications dans research.html
function initCommsToggle() {
    const toggleBtn = document.getElementById('toggle-comms-btn');
    const extraComms = document.getElementById('extra-comms');

    if (toggleBtn && extraComms) {
        toggleBtn.addEventListener('click', () => {
            const isHidden = extraComms.classList.contains('hidden');

            if (isHidden) {
                // Afficher le reste
                extraComms.classList.remove('hidden');
                // Changer le texte et l'icône du bouton
                toggleBtn.innerHTML = `
                    Réduire
                    <span class="material-symbols-outlined text-sm">expand_less</span>
                `;
            } else {
                // Cacher le reste
                extraComms.classList.add('hidden');
                // Remettre le texte et l'icône par défaut
                toggleBtn.innerHTML = `
                    Afficher tout
                    <span class="material-symbols-outlined text-sm">expand_more</span>
                `;

                // Optionnel : faire remonter la vue un peu plus haut pour ne pas être perdu en fermant
                toggleBtn.closest('section').scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
}


// Fonction pour le carousel des médias (défilement infini au survol)
function initMediaCarousel() {
    const track = document.getElementById('carousel-track');
    const carousel = document.getElementById('media-carousel');
    const scrollLeftBtn = document.getElementById('scroll-left');
    const scrollRightBtn = document.getElementById('scroll-right');

    if (!track || !carousel || !scrollLeftBtn || !scrollRightBtn) return;

    // 1. Cloner les éléments pour l'effet de boucle infinie
    const items = Array.from(track.children);
    items.forEach(item => {
        const clone = item.cloneNode(true);
        track.appendChild(clone);
    });

    let isScrolling = false;
    let scrollDirection = 0;
    const scrollSpeed = 2; // Vitesse de défilement 

    const scrollLoop = () => {
        if (!isScrolling) return;

        // La largeur de la moitié du track correspond à la largeur de nos 5 items originaux
        const halfWidth = track.scrollWidth / 2;

        // Si on essaie de scroller vers la gauche alors qu'on est au tout début (0)
        // On se téléporte instantanément au milieu (le début des clones) pour continuer
        if (scrollDirection === -1 && carousel.scrollLeft <= 0) {
            carousel.scrollLeft += halfWidth;
        }

        // On applique le défilement
        carousel.scrollLeft += scrollDirection * scrollSpeed;

        // Si on a scrollé vers la droite et qu'on dépasse la largeur de nos éléments originaux
        // On se téléporte instantanément au début pour créer la boucle
        if (scrollDirection === 1 && carousel.scrollLeft >= halfWidth) {
            carousel.scrollLeft -= halfWidth;
        }

        requestAnimationFrame(scrollLoop);
    };

    // Gestion du survol - Zone Gauche
    scrollLeftBtn.addEventListener('mouseenter', () => {
        isScrolling = true;
        scrollDirection = -1;
        requestAnimationFrame(scrollLoop);
    });
    scrollLeftBtn.addEventListener('mouseleave', () => {
        isScrolling = false;
    });

    // Gestion du survol - Zone Droite
    scrollRightBtn.addEventListener('mouseenter', () => {
        isScrolling = true;
        scrollDirection = 1;
        requestAnimationFrame(scrollLoop);
    });
    scrollRightBtn.addEventListener('mouseleave', () => {
        isScrolling = false;
    });

    // Défilement infini sur mobile 
    carousel.addEventListener('scroll', () => {
        if (!isScrolling) {
            const halfWidth = track.scrollWidth / 2;
            if (carousel.scrollLeft <= 0) {
                carousel.scrollLeft += halfWidth;
            } else if (carousel.scrollLeft >= halfWidth) {
                carousel.scrollLeft -= halfWidth;
            }
        }
    });
}
