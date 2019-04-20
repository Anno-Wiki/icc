<script>
    function select() {
        var userSelection = window.getSelection();
        var rangeObject = userSelection.getRangeAt(0);

        // The first and last containers
        var topel = rangeObject.startContainer.parentNode
        console.log(topel);
        var firstl = topel.parentNode.id;
        var lastl = rangeObject.endContainer.parentNode.parentNode.id;

        // The offets of the first and last chars
        // These numbers are (inclusive, exclusive)
        var firstc = rangeObject.startOffset;
        var lastc = rangeObject.endOffset;

        var pos = topel.getBoundingClientRect();
        var btn = document.getElementById('line-form-submit')

        var posTop = pos.top + document.documentElement.scrollTop;
        btn.style.top = posTop + "px";
        console.log(btn.style.bottom);
        var length = pos.right - pos.left;
        var half = length / 2;
        var left = pos.left + half;
        btn.style.left = pos.left + "px";
    }
    function init() {
        document.addEventListener('onmouseup', select);
        document.addEventListener('onmousedown', select);
        document.addEventListener('onselectionchange', select);
    };
    document.addEventListener('DOMContentLoaded', init, false);
</script>
