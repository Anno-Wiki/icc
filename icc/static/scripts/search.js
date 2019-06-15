atload(function () {
    let glass = byID('magglass');
    let box = byID('search');
    let input = byTag(box, 'input')[0];
    let nav = byTag(document, 'nav')[0];
    const tabletBreak = 1024;

    function inputActive() { return document.activeElement === input; }
    function hideSearch() {
        if (windowSize() <= tabletBreak) {
            if (!inputActive()) input.classList.add('hide');
        } else input.classList.remove('hide');
    }

    // test windowsize and hide the search initially and whenever the window is resized
    window.addEventListener('resize', hideSearch);
    hideSearch();

    document.addEventListener('click', function (evt) {
        // clicking anywhere hides the searchbox if it isn't in the searchbox
        if (windowSize() <= tabletBreak && ![...byTag(box, '*')].includes(evt.target)) {
            nav.classList.remove('searching');
            input.classList.add('hide');
        }
    });

    // simulate focus border for input construction
    setInterval(function () { box.style.border = inputActive() ? '1px solid #b58900' : ''; }, 100);

    glass.onclick = function () {
        // submit if search is open, otherwise show it
        if (!input.classList.contains('hide') && nav.classList.contains('searching') || windowSize() > tabletBreak){
            if (input.value != '')
                box.submit();
        } else {
            nav.classList.toggle('searching');
            input.classList.toggle('hide');
            input.focus();
        }
    };
});
