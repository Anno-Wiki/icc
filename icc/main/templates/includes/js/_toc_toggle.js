<script>
    function toggle(x) {
        let level = x.parentNode.className.replace(/[a-z]*/g, '');
        let subgroups = [...byCls(x.parentNode, `grouping${Number(level)+1}`)];
        console.log(subgroups);
        subgroups.forEach((grp) => grp.style.display = grp.style.display == 'none' ? '' : 'none');
    }

    atload(function () {
        let groups = [];
        for (let i = 2; i <= 5; i++)
            groups.push([...allof(`grouping${i}`)]);
        groups = [].concat.apply([], groups);
        for (let i = 0; i < groups.length; i++)
            groups[i].style.display = 'none';
    });
</script>
