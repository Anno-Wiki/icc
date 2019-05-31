<script>
    function showBtn() {
        var sel = window.getSelection();
        var btn = byID("annotate-button");

        if (sel.toString() == "") {
            // Nothing to see here, abandon ship.
            btn.style.display = "";
            return;
        }

        // It's showtime.
        btn.style.display = "block";
    }

    function procSel() {
        var sel = window.getSelection();

        var ranges = [];
        for (let i = 0; i < sel.rangeCount; i++) {
            // get all the ranges
            ranges[i] = sel.getRangeAt(i);
        }

        // first and last lines
        fl = parentNumID(ranges[0].startContainer);
        ll = parentNumID(ranges[ranges.length-1].endContainer);
        // first and last characters
        fc = ranges[0].startOffset;
        lc = ranges[ranges.length-1].endOffset;
    }

    function submit() {
        procSel();
        var url = ["/annotate/{{ text.url_name }}/edition/{{ edition.num }}/{{ toc.id }}/", fl, "/", ll, "?fc=", fc, "&lc=", lc];
        location.href = url.join("");
    }

    atload(function () {
        var btn = byID("annotate-button");
        //btn.addEventListener("pointerenter", procSel);
        //btn.addEventListener("pointerover", procSel);

        // prevent deselection when click button
        btn.addEventListener("mousedown", (evt) => evt.preventDefault());
        btn.addEventListener("click", submit);
        setInterval(showBtn, 100);
    });
</script>
