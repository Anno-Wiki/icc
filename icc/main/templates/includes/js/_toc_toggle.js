<script>
    function toggle(x) {
        cls = x.parentNode.parentNode.classList[1];
        elements = allof(cls);

        if (elements[1].style.display == 'none') {
            for (let i = 1; i < elements.length; i++)
                elements[i].style.display = '';
            x.innerHTML = '[ - ]'
        } else {
            for (let i = 1; i < elements.length; i++)
                elements[i].style.display = 'none';
            x.innerHTML = '[ + ]'
        }
    }

    atload(function () {
        levels = [];
        for (let i = 2; i <= 5; i++)
            levels.push([...allof(`lvl${i}`)]);
        levels = levels.flat();
        for (let i = 0; i < levels.length; i++)
            levels[i].style.display = 'none';
    });
</script>
