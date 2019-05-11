<script>
    function showAnnotation(x) {
        // The id for the annotation is within the <sup> in the childNodes
        var aid = 'a' + byTag(x, 'sup')[0].innerHTML.replace(/[\[\]]/g, '');
        var annotation = byID(aid);

        // if the element already exists, don't create it again!
        if (byID(aid + '-js')) { return; }

        var newAnnotation = annotation.cloneNode(true);
        newAnnotation.id = newAnnotation.id + '-js';

        // change the collapse to a kill button
        var newCollapse = byCls(newAnnotation, 'collapse');
        for (var i = 0; i < newCollapse.length; i++) {
            // there are might be more than one  collapse for formatting reasons
            newCollapse[i].innerHTML = '&times;';
            newCollapse[i].onclick = function () {
                var annotation = parentNum(this, 'a');
                annotation.parentNode.removeChild(annotation);
            }
        }

        // blast everything in the center but the footnote and the lock icon
        var center = byCls(newAnnotation, 'center')[0];
        for (var i = 0; i < center.childNodes.length; i++) {
            if (center.childNodes[i].className != 'footnote') {
                center.childNodes[i].innerHTML = '';
            }
        }

        // insert new annotation into the dom after the line
        byID('text-content').insertBefore(newAnnotation, parentNum(x).nextSibling);
    }
    atload(function () {
        // convert the links to buttons for the script
        var links = allof('annotation-link');
        for (var i = 0; i < links.length; i++) {
            links[i].removeAttribute('href');
            links[i].style.cursor = 'pointer';
        }
    });
</script>
