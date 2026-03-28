// script pour le bouton de copie d'email
const emailToCopy = 'amet.sorbonne@gmail.com';
document.getElementById('copyEmailBtn').addEventListener('click', async () => {
    try {
        await navigator.clipboard.writeText(emailToCopy);
        const toast = document.createElement('div');
        toast.textContent = 'Email copié !';
        toast.className = 'fixed bottom-6 right-6 bg-emerald-700 text-white text-sm px-4 py-2 rounded shadow-lg';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2200);
    } catch (err) {
        alert('Impossible de copier l\'email. Veuillez le copier manuellement : ' + emailToCopy);
    }
});
// script pour le menu mobile
const mobileMenuBtn = document.getElementById('mobile-menu-btn');
const navLinks = document.getElementById('nav-links');
const menuIcon = mobileMenuBtn.querySelector('.material-symbols-outlined');

mobileMenuBtn.addEventListener('click', () => {
    // Bascule l'affichage du menu
    navLinks.classList.toggle('hidden');
    navLinks.classList.toggle('flex');

    // Change l'icône hamburger en croix quand le menu est ouvert
    if (navLinks.classList.contains('hidden')) {
        menuIcon.textContent = 'menu';
    } else {
        menuIcon.textContent = 'close';
    }
});