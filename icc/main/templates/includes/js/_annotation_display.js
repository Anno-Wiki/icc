<script>
    function showAnnotation(x) {
        // The id for the annotation is within the <sup> in the childNodes
        let aid = `a${byTag(x, 'sup')[0].innerHTML.replace(/[\[\]]/g, '')}`;
        let newID = `js${aid}`;
        let annotation = byID(aid);

        // if the element already exists, don't create it again!
        if (byID(newID)) { return; }

        let newAnnotation = annotation.cloneNode(true);
        newAnnotation.id = newID;

        // change the collapse to a kill button
        let newCollapse = byCls(newAnnotation, 'collapse');
        for (let i = 0; i < newCollapse.length; i++) {
            // there might be more than one  collapse for formatting reasons
            newCollapse[i].innerHTML = '&times;';
            newCollapse[i].onclick = function () {
                let annotation = byID(newID);
                annotation.parentNode.removeChild(annotation);
            }
        }

        // blast everything in the center but the footnote and the lock icon
        let center = first(newAnnotation, 'center');
        for (let i = 0; i < center.childNodes.length; i++)
            if (center.childNodes[i].className != 'footnote')
                center.childNodes[i].innerHTML = '';

        let updown = byTag(first(newAnnotation, 'arrows'), 'a');
        for (let i = 0; i < updown.length; i++) {
            updown[i].dataset.parent = newID;
            updown[i].id = `${updown[i].dataset.direction}-${newID}`;
        }

        // insert new annotation into the dom after the line
        byID('text-content').insertBefore(newAnnotation, parentNum(x).nextSibling);
    }
    atload(function () {
        // convert the links to buttons for the script
        let links = allof('annotation-link');
        for (let i = 0; i < links.length; i++) {
            links[i].removeAttribute('href');
            links[i].style.cursor = 'pointer';
        }
    });
</script>
