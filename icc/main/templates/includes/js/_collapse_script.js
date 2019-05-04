<script>
    function collapse(x) {
        var annotation = x.closest(".annotation")
        var collapsible = byCls(annotation, "annotation-collapsible")[0];
        if (collapsible.style.display == "none") {
            collapsible.style.display = "block";
            annotation.style.borderRadius = "0";
            annotation.style.borderTopLeftRadius = "20px";
            annotation.style.borderTopRightRadius = "20px";
            x.innerHTML = "[ - ]";
        } else {
            x.innerHTML = "[ + ]";
            collapsible.style.display = "none";
            annotation.style.borderRadius = "20px";
        }
    }
</script>
