document.addEventListener('DOMContentLoaded', function () {
    const themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) return;

    function setTheme(theme) {
        document.body.className = theme;
        localStorage.setItem('theme', theme);
        themeToggle.textContent = theme === 'light' ? 'Modo Oscuro' : 'Modo Claro';
    }

    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);

    themeToggle.addEventListener('click', function () {
        const nextTheme = document.body.className === 'light' ? 'dark' : 'light';
        setTheme(nextTheme);
    });
});
