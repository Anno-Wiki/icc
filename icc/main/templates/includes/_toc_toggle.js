<script>
    function toggle(x) {
        cls = x.parentNode.parentNode.classList[1];
        elements = document.getElementsByClassName(cls);
        if (elements[1].style.display == "" || elements[1].style.display == "none") {
            for (var i = 1; i < elements.length; i++) {
                elements[i].style.display = "table-row";
            }
            x.innerHTML = "[ - ]"
        } else {
            for (var i = 1; i < elements.length; i++) {
                elements[i].style.display = "none";
            }
            x.innerHTML = "[ + ]"
        }
    }
</script>
