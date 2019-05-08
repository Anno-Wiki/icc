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
        var url = ["/annotate/{{ text.url_name }}/edition/{{ edition.num }}/", fl, "/", ll, "?fc=", fc, "&lc=", lc];
        location.href = url.join("");
    }


    document.addEventListener("DOMContentLoaded", function () {
        var textBlock = document.getElementById("text-content");
        // these don't work and idk why
        textBlock.addEventListener("selectionstart", showBtn);
        textBlock.addEventListener("selectionchange", showBtn);

        // for web
        textBlock.addEventListener("mousedown", showBtn);
        textBlock.addEventListener("mouseup", showBtn);
        textBlock.addEventListener("dblclick", showBtn);

        // for mobile
        textBlock.addEventListener("touchcancel", showBtn);
        textBlock.addEventListener("touchend", showBtn);
        textBlock.addEventListener("touchenter", showBtn);
        textBlock.addEventListener("touchleave", showBtn);
        textBlock.addEventListener("touchmove", showBtn);
        textBlock.addEventListener("touchstart", showBtn);

        var btn = byID("annotate-button");
        btn.addEventListener("pointerenter", procSel);
        btn.addEventListener("pointerover", procSel);
        setInterval(showBtn, 100);
    });
</script>
