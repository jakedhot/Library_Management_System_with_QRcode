const sidebar = window.location.pathname;

const navLinks = document.querySelectorAll('ul a').forEach(link => {
    if(link.href.includes(`${sidebar}`)){
        link.classList.add('active');
    }
    })