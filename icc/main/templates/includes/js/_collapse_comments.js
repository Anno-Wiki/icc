<script nonce="{{ csp_nonce() }}">
    atload(function () {
        let comments = allof('comment');
        [...comments].forEach(function(comment) {
            let replies = [...comment.childNodes].filter(el => el.className == 'reply');
            for (let i = 0; i < replies.length; i++) {
                collapseThread(byCls(replies[i], 'collapse')[0]);
            }
        });
    });
    function collapseThread(evt) {
        let comment = parentByCls(this, '(comment|reply)')
        let replies = [...comment.childNodes].filter(el => el.className == 'reply');
        let commentBody = byCls(comment, 'comment-body')[0];
        let isCollapsed = commentBody.style.display == 'none';
        commentBody.style.display = isCollapsed ? '' : 'none';
        this.innerHTML = isCollapsed ? '[ - ]' : `[ +${this.dataset['count']} ]`;
        if (replies.length < 1)
            return;
        if (isCollapsed) {
            replies.forEach(el => el.style.display = '');
            toggleBorderRadius(comment, false);
        } else {
            replies.forEach(el => el.style.display = 'none');
            toggleBorderRadius(comment, true);
        }
    }
    function toggleBorderRadius(this, close) {
        if (this.className != 'comment')
            return;
        else if (close)
            this.style.borderRadius = '20px';
        else
            this.style.borderRadius = '';
    }
</script>
