<script>
    atload(function () {
        let arrows = allof('arrows');
        for (let i = 0; i < arrows.length; i++) {
            let updown = byTag(arrows[i], 'a');
            for (let j = 0; j < updown.length; j++) {
                updown[j].removeAttribute('href');
                updown[j].style.cursor = 'pointer';
            }
        }
    });
    function loginNext(id, entity, up) {
        // just a minor complexity reducer for upvote/downvote
        // if the user is not logged in, redirect him to the login with
        // the next param being to upvote the annotation and the next
        // param after that being the page he is currently on
        let next = [
            '{{ url_for('main.vote') }}',
            '?',
            `id=${id}`,
            `&entity=${entity}`,
            `&up=${up}`,
            `&next=${window.location.pathname}`
        ]
        return `{{ url_for('main.login') }}?next=${escape(next.join(''))}`;
    }

    function vote(x, up) {
        let entity = byID(x.dataset.parent);
        let xhttp = new XMLHttpRequest();
        xhttp.onload = function () {
            let data = JSON.parse(this.responseText);
            let weight = first(entity, 'weight');
            if (data.status == 'login') {
                location.href = loginNext(x.dataset.parent, x.dataset.entity, up);
                return;
            }
            if (data.rollback) {
                if (data.success) {
                    x.className = up ? 'up' : 'down';
                    opposite = up ? 'down' : 'up'
                    byID(`${opposite}-${x.dataset.parent}`).className = '';
                } else { x.className = ''; }
            } else if(data.success) { x.className = 'up'; }
            if ('change' in data)
                modWeight(weight, data.change);
            flashMessages();
        }
        url = [
            '{{ url_for('ajax.vote') }}',
            '?',
            `id=${x.dataset.parent}`,
            `&entity=${x.dataset.entity}`,
            `&up=${up}`
        ]
        xhttp.open('GET', url.join(''), true);
        xhttp.send();
    }

    function modWeight(weight, change) {
        let points = Number(weight.innerHTML);
        let newPoints = points + change;

        let poppers = [];
        let pushers = [];
        if (newPoints > 0) {
            poppers = ['down', 'nil'];
            pushers = ['up'];
        } else if (newPoints < 0) {
            poppers = ['up', 'nil'];
            pushers = ['down'];
        } else {
            poppers = ['up', 'down'];
            pushers = ['nil'];
        }
        pushers.forEach(function(el) { weight.classList.add(el) });
        poppers.forEach(function(el) { weight.classList.remove(el) });
        weight.innerHTML = `${newPoints} `;
    }
</script>
