<script nonce="{{ csp_nonce() }}">
    atload(function () {
        // get the  inputs make them global
        totalLines = {{ edition.lines.count() }};
        flInput = byID('first_line');
        llInput = byID('last_line');

        // This is to override firefox's form caching, which wreaks havoc with
        // my js script. Eventually I'll have to make this work even with the
        // caching, but for now (and a while going forward) this is good enough.
        let first_line = byID('first_line_cache');
        let last_line = byID('last_line_cache');
        if (first_line != null && last_line != null) {
            flInput.value = first_line.innerHTML;
            llInput.value = last_line.innerHTML;
        }

        // hide the text line inputs because they ugly
        flInput.parentNode.style.display = 'none';
        llInput.parentNode.style.display = 'none';
        // make the expanders
        genExpander(true);
        genExpander(false);
    });

    function newLine(cls, num, line) {
        let lineEl = newEl('div', `line ${cls}`);
        lineEl.id = num;
        let numEl = newEl('span', 'line-num');
        numEl.innerHTML = num;
        lineEl.appendChild(numEl);
        let textEl = newEl('span', 'text');
        // make sure you post an hr if it's an hr
        textEl.innerHTML = cls == 'hr' ? '<hr>' : line;
        lineEl.appendChild(textEl);
        return lineEl;
    }

    function contract(evt) {
        if (flInput.value == llInput.value) { return; }
        let expander = evt.target.parentNode; // the expander element
        let topExpander = expander.classList.contains('up');
        let input = topExpander ? flInput : llInput;
        let change = topExpander ? 1 : -1;
        let block = expander.parentNode; // the block in which is everything

        let lines = allof('line');
        let line = byID(input.value);

        line.classList.remove('selection');

        if (topExpander) {
            let countAbove = 0;
            for (let i = 0; i < [...lines].indexOf(line); i++)
                if (!lines[i].classList.contains('selection'))
                    countAbove++;
            block.removeChild(line);
            block.insertBefore(line, expander);
            if (countAbove >= 3) block.removeChild(lines[0]);
        } else {
            let countBelow = 0;
            for (let i = lines.length-1; i > [...lines].indexOf(line); i--)
                if (!lines[i].classList.contains('selection'))
                    countBelow++;
            block.removeChild(expander);
            block.insertBefore(expander, line);
            if (countBelow >= 3) block.removeChild(lines[lines.length-1]);
        }
        input.value = Number(input.value) + change;
    }

    function expand(evt) {
        let expander = evt.target.parentNode; // the expander element
        let block = expander.parentNode; // the block in which is everything
        let topExpander = expander.classList.contains('up');
        let input = topExpander ? flInput : llInput;
        let change = topExpander ? -1 : 1;
        let lineToHighlight = Number(input.value) + change;
        if (lineToHighlight > totalLines || lineToHighlight < 1) { return; }

        // the line to be gotten by ajax
        let lines = allof('line');
        let lineToGet = topExpander ? Number(lines[0].id)-1 : Number(lines[lines.length-1].id)+1;

        xhttp = new XMLHttpRequest();
        xhttp.onload = function () {
            data = JSON.parse(this.responseText);
            if(data.success) {
                // the line to be added to the body in the context
                let lineElToAdd = newLine(data.enum, lineToGet, data.line);
                // the line to be highlighted in the selection
                let lineElToHighlight = byID(lineToHighlight);
                lineElToHighlight.classList.add('selection');
                if (topExpander) {
                    block.insertBefore(lineElToAdd, lines[0]);
                    block.removeChild(expander);
                    block.insertBefore(expander, lineElToHighlight);
                } else {
                    block.appendChild(lineElToAdd);
                    block.removeChild(lineElToHighlight);
                    block.insertBefore(lineElToHighlight, expander);
                }
                input.value = lineToHighlight;
            } else if (lineToHighlight > 1 || lineToHighlight <= totalLines){
                // no new line, but need to expand
                let lineElToHighlight = byID(lineToHighlight);
                lineElToHighlight.classList.add('selection');
                if (topExpander) {
                    block.removeChild(expander);
                    block.insertBefore(expander, lineElToHighlight);
                } else if (lineToHighlight) {
                    block.removeChild(lineElToHighlight);
                    block.insertBefore(lineElToHighlight, expander);
                }
                input.value = lineToHighlight;
            }
        }
        let url = `{{ url_for('ajax.line', toc_id=lines[0].toc.id) }}?num=${lineToGet}`;
        xhttp.open('GET', url, true);
        xhttp.send();
    }

    function genExpander(topExpander) {
        let lineNum =  topExpander ? flInput.value : llInput.value;
        let cls = topExpander ? 'expander up' : 'expander down';

        // up and down arrows
        let up = newEl('div', 'uparr');
        up.onclick = topExpander ? expand : contract;

        let down = newEl('div', 'downarr');
        down.onclick = topExpander ? contract : expand;

        // the middle hr
        let middle = newEl('hr', 'expander');

        // the container
        let expander = newEl('div', cls);
        expander.appendChild(up);
        expander.appendChild(middle);
        expander.appendChild(down);

        let line = byID(lineNum);
        if (topExpander) {
            line.parentNode.insertBefore(expander, line);
        } else {
            line.parentNode.insertBefore(expander, line.nextSibling);
        }
    }
</script>
