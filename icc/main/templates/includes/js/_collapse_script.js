<script>
    function collapse(x) {
        var annotation = parentByCls(x, '^annotation$')
        var collapsible = byCls(annotation, 'annotation-collapsible')[0];
        if (collapsible.style.display == 'none') {
            collapsible.style.display = '';
            annotation.style.borderRadius = '';
            x.innerHTML = '[ - ]';
        } else {
            x.innerHTML = '[ + ]';
            collapsible.style.display = 'none';
            annotation.style.borderRadius = '20px';
        }
    }
</script>
