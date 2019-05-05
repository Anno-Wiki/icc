<script>
    function show_annotate_button() {
        var sel = window.getSelection();
        var btn = document.getElementById("annotate-button");

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


    document.addEventListener("DOMContentLoaded", function () {
        var theblock = document.getElementById("text-content");
        theblock.addEventListener("mousedown", show_annotate_button);
        theblock.addEventListener("mouseup", show_annotate_button);
        theblock.addEventListener("dblclick", show_annotate_button);

        theblock.addEventListener("touchcancel", show_annotate_button);
        theblock.addEventListener("touchend", show_annotate_button);
        theblock.addEventListener("touchenter", show_annotate_button);
        theblock.addEventListener("touchleave", show_annotate_button);
        theblock.addEventListener("touchmove", show_annotate_button);
        theblock.addEventListener("touchstart", show_annotate_button);

        var btn = document.getElementById("annotate-button");
        btn.addEventListener("pointerenter", proc_selection);
        btn.addEventListener("pointerover", proc_selection);
    });
    setInterval(showBtn, 100);
</script>
