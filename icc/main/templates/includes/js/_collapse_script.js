<script nonce="{{ csp_nonce() }}">
    function collapse(evt) {
        var annotation = parentByCls(this, '^annotation$')
        var collapsible = byCls(annotation, 'annotation-collapsible')[0];
        if (collapsible.style.display == 'none') {
            collapsible.style.display = '';
            annotation.style.borderRadius = '';
            this.innerHTML = '[ - ]';
        } else {
            this.innerHTML = '[ + ]';
            collapsible.style.display = 'none';
            annotation.style.borderRadius = '20px';
        }
    }
    atload(function() { [...allof('collapse')].forEach(el => el.onclick = collapse)});
</script>
