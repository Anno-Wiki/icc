<script>
    function collapse(x) {
        var annotation = x.closest(".annotation")
        var collapsible = annotation.querySelector(".annotation-collapsible");
        if (collapsible.style.display == "none") {
            collapsible.style.display = "block";
            annotation.style.borderRadius = "0";
            annotation.style.borderTopLeftRadius = "10px";
            annotation.style.borderTopRightRadius = "10px";
            x.innerHTML = "[ - ]";
        } else {
            x.innerHTML = "[ + ]";
            collapsible.style.display = "none";
            annotation.style.borderRadius = "10px";
        }
    }
</script>
