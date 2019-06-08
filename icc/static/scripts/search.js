atload(function () {
    let glass = byID('magglass');
    let box = byID('search');
    let input = byTag(box, 'input')[0];
    let nav = byTag(document, 'nav')[0];

    window.addEventListener('resize', function () {
        let inputactive = document.activeElement === input;
        if (document.documentElement.clientWidth <= 1024) {
            if (!inputactive) input.classList.add('hide');
        } else input.classList.remove('hide');
    });

    if (document.documentElement.clientWidth <= 1024)
        if (document.activeElement !== input) input.classList.add('hide');

    document.addEventListener('click', function (evt) {
        if (![...box.childNodes].includes(evt.target) && ![...glass.childNodes].includes(evt.target)) {
            nav.classList.remove('searching');
            input.classList.add('hide');
        }
    });

    setInterval(function () {
        let input = byTag(byID('search'), 'input')[0];
        let inputactive = document.activeElement === input;
        if (inputactive) box.style.border = '1px solid #b58900';
        else box.style.border = '';}, 100);

    glass.onclick = function () {
        if (!input.classList.contains('hide') && nav.classList.contains('searching'))
            box.submit();
        else {
            nav.classList.toggle('searching');
            input.classList.toggle('hide');
            input.focus();
        }
    };
});
