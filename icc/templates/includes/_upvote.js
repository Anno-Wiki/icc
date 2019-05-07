<script>
    atLoad(function () {
        let arrows = allof("arrows");
        for (let i = 0; i < arrows.length; i++) {
            let updown = arrows[i].byTag("a");
            for (let j = 0; j < updown; j++) {
                updown[j].removeAttribute("href");
            }
        }
    });
</script>
