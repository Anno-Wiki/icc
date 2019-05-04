<script>
    function kill_annotation(x) {
        var annotation = get_parent(x, "a");
        annotation.parentNode.removeChild(annotation);
    }
    function show_annotation(x) {
        // The id for the annotation is within the super in the childNodes
        var aid = "a" + x.childNodes[0].innerHTML.replace(/[\[\]]/g, "");
        var annotation = document.getElementById(aid);

        // if the element already exists, don't create it again!
        var if_exist = document.getElementById(aid + "-js");
        if (if_exist) {
            return;
        }

        // clone annotation
        var new_annotation = annotation.cloneNode(true);

        // change annotation id
        new_annotation.id = new_annotation.id + "-js";

        // change the collapse to a kill button
        var new_collapse = new_annotation.getElementsByClassName("collapse");
        for (var i = 0; i < new_collapse.length; i++) {
            new_collapse[i].innerHTML = "&times;";
            new_collapse[i].setAttribute("onclick", "kill_annotation(this);");
        }

        // blast everything but the footnote and the lock icon
        var center = new_annotation.querySelector(".center");
        for (var i = 0; i < center.childNodes.length; i++) {
            if (center.childNodes[i].className != "footnote") {
                center.childNodes[i].innerHTML = "";
            }
        }

        // insert new annotation into the dom after the line
        var container = document.getElementById("text-content");
        container.insertBefore(new_annotation, x.parentNode.parentNode.nextSibling);
    }
    document.addEventListener("DOMContentLoaded", function() {
        var links = document.getElementsByClassName("annotation-link");
        for (var i = 0; i < links.length; i++) {
            links[i].removeAttribute("href");
            links[i].style.cursor = "pointer";
        }
    });
</script>
