<script>
    function show() {
        var btn = document.getElementById("annotate-button");
        var sel = window.getSelection();

        if (sel.toString() == "") {
            // Nothing is highlighted, abandon ship.
            btn.style.display = "";
            return;
        }

        // It's showtime.
        btn.style.display = "block";
    }

    function proc_selection() {
        var sel = window.getSelection();

        var ranges = [];
        for (let i = 0; i < sel.rangeCount; i++) {
            // get all the ranges (weird model)
            ranges[i] = sel.getRangeAt(i);
        }

        // first and last lines
        firstl = get_parent_id(ranges[0].startContainer);
        lastl = get_parent_id(ranges[ranges.length-1].endContainer);
        // first and last characters
        firstc = ranges[0].startOffset;
        lastc = ranges[ranges.length-1].endOffset;
    }
    function submit() {
        var url = ["/annotate/{{ text.url_name }}/edition/{{ edition.num }}/", firstl, "/", lastl, "?fc=", firstc, "&lc=", lastc];
        location.href = url.join("");
    }


    function init() {
        var theblock = document.getElementById("text-content");
        theblock.addEventListener("mousedown", show);
        theblock.addEventListener("mouseup", show);
        theblock.addEventListener("dblclick", show);

        theblock.addEventListener("touchcancel", show);
        theblock.addEventListener("touchend", show);
        theblock.addEventListener("touchenter", show);
        theblock.addEventListener("touchleave", show);
        theblock.addEventListener("touchmove", show);
        theblock.addEventListener("touchstart", show);

        var btn = document.getElementById("annotate-button");
        btn.addEventListener("pointerenter", proc_selection);
        btn.addEventListener("pointerover", proc_selection);
    }
    document.addEventListener("DOMContentLoaded", init);
</script>
