<script>
    function select() {
        var btn = document.getElementById("line-form");
        var sel = window.getSelection();

        if (sel.toString() == "") {
            // Nothing is highlighted, abandon ship.
            btn.style.display = "";
            return;
        }

        var ranges = [];
        for (let i = 0; i < sel.rangeCount; i++) {
            ranges[i] = sel.getRangeAt(i);
        }

        // first and last lines
        var firstl = ranges[0].startContainer.parentNode.parentNode.id;
        var lastl = ranges[ranges.length-1].endContainer.parentNode.parentNode.id;

        // The offets of the first and last chars
        // These numbers are (inclusive, exclusive)
        var firstc = ranges[0].startOffset;
        var lastc = ranges[ranges.length-1].endOffset;

        // Populate the form
        var form = document.getElementById("line-form");
        var firstLField = form.querySelector("#first_line");
        firstLField.value = firstl;
        var lastLField = form.querySelector("#last_line");
        lastLField.value = lastl;
        var firstCField = form.querySelector("#first_char");
        firstCField.value = firstc;
        var lastCField = form.querySelector("#last_char");
        lastCField.value = lastc;

        // It's showtime.
        btn.style.display = "block";
    }
    function init() {
        var theblock = document.getElementById("text-content");
        theblock.addEventListener("mousedown", select);
        theblock.addEventListener("mouseup", select);
        theblock.addEventListener("dblclick", select);
    }
    document.addEventListener("DOMContentLoaded", init);
</script>
