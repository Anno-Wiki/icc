$(document).ready(function(){
    
    var get_selection = function (event){
        if (window.getSelection) { // non-IE
            var userSelection = window.getSelection();
            var rangeObject = userSelection.getRangeAt(0);
            if (rangeObject.startContainer == rangeObject.endContainer) {
                return rangeObject.startContainer.parentNode.id;
            } else {
                ids = []
                ids.push(rangeObject.startContainer.parentNode.id);
                ids.push(rangeObject.endContainer.parentNode.id);
                return ids
            }

        } else if (document.selection) { // IE lesser
            var userSelection = document.selection.createRange();
            var ids = [];
            
            if (userSelection.htmlText.toLowerCase().indexOf('word') >= 0) {
                $(userSelection.htmlText).filter('word').each(function(index, word) {
                    ids.push(word.id);
                });
                return ids;
            } else {
                return userSelection.parentElement().id;
            }
        }
    };


    document.addEventListener('selectionchange', function() {
        if(window.getSelection().toString() !== ''){
            $(".linker").css('visibility', 'visible');
        }
        else{
            $(".linker").css('visibility', 'hidden');
        }

    });

    var modal = $("#linkerbox");
    var btn = $(".linker")[0];
    var word = $(".close")[0];
    btn.onclick = function() {
        $('#selection').text(window.getSelection().toString());
        $('#tags').text(get_selection());
        modal.css('display','block');
    };
    word.onclick = function() {
        modal.css('display','none');
    };
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.css('display','none');
        }
    };

});
