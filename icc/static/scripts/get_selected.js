$(document).ready(function(){
    

    document.addEventListener('selectionchange', function() {
        if(window.getSelection().toString() !== ''){
            $(".linker").css('visibility', 'visible');
        }
        else{
            $(".linker").css('visibility', 'hidden');
        }

    });

    var modal = $("#linkerbox");
    var btn = $(".linker");
    var close = $(".close");
    btn.click(function() {
        // The main vars
        var userSelection = window.getSelection();
        var rangeObject = userSelection.getRangeAt(0);

        // The first and last containers
        var firstl = rangeObject.startContainer.parentNode.id;
        var lastl = rangeObject.endContainer.parentNode.id;

        // The offets of the first and last chars
        // These numbers are (inclusive, exclusive)
        var firstc = rangeObject.startOffset;
        var lastc = rangeObject.endOffset;

        $('#selection').text(userSelection.toString());

        $('#first_line').val(firstl);
        $('#last_line').val(lastl);

        $('#first_char_idx').val(firstc);
        $('#last_char_idx').val(lastc);

        modal.css('display','block');
    });

    close.click(function() {
        modal.css('display','none');
    });

    // I don't know what this function does and I am going to leave it commented
    // out until I find something broken.
/*    window.onclick = function(event) {
        if (event.target == modal) {
            modal.css('display','none');
        }
    };*/

});
