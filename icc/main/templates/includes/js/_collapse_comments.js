<script>
    atLoad(function () {
        let comments = allof('comment');
        [...comments].forEach(function(comment) {
            let replies = [...comment.childNodes].filter(el => el.className == 'reply');
            for (let i = 0; i < replies.length; i++)
                collapseThread(byCls(replies[i], 'collapse')[0]);
        });
    });
    function collapseThread(x) {
        let comment = parentByCls(x, '(comment|reply)')
        let replies = [...comment.childNodes].filter(el => el.className == 'reply');
        let commentBody = byCls(comment, 'comment-body')[0];
        let isCollapsed = commentBody.style.display == 'none';
        commentBody.style.display = isCollapsed ? '' : 'none';
        x.innerHTML = isCollapsed ? '[ - ]' : `[ +${x.dataset['count']} ]`;
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
    function toggleBorderRadius (x, close) {
        if (x.className != 'comment')
            return;
        else if (close)
            x.style.borderRadius = '20px';
        else
            x.style.borderRadius = '';
    }
</script>
