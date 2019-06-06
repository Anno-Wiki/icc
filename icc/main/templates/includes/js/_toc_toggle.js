<script nonce="{{ csp_nonce() }}">
    function toggle(evt) {
        let level = this.parentNode.className.replace(/[a-z]*/g, '');
        let subgroups = [...byCls(this.parentNode, `grouping${Number(level)+1}`)];
        subgroups.forEach((grp) => grp.style.display = grp.style.display == 'none' ? '' : 'none');
    }

    atload(function () {
        let groups = [];
        for (let i = 2; i <= 5; i++)
            groups.push([...allof(`grouping${i}`)]);
        groups = [].concat.apply([], groups);
        for (let i = 0; i < groups.length; i++)
            groups[i].style.display = 'none';
        [...allof('outer')].forEach(el => { if (el.dataset.haslines == 'False') el.onclick = toggle });
    });
</script>
