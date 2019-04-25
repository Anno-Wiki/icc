<script>
    function show_annotation(x) {
        var aid = "a" + x.childNodes[0].innerHTML.replace(/[\[\]]/g, "");
        console.log(aid);
        var annotation = document.getElementById(aid);
        annotation.classList.add("js-show");
    }
    document.addEventListener("DOMContentLoaded", function() {
        var links = document.getElementsByClassName("annotation-link");
        for (var i = 0; i < links.length; i++) {
            links[i].removeAttribute("href");
            links[i].style.cursor = "pointer";
        }
    });
</script>
