<script>
    var lastServerTime;

    function checkTime() {
        fetch('/ajax/heartbeat')
            .then(function (response) {
                return response.json();
            })
            .then(function (json) {
                if (!lastServerTime) {
                    lastServerTime = json.start_time;
                } else if (lastServerTime != json.start_time) {
                    window.location.reload();
                }
            });
    }

    setInterval(checkTime, 1000);
</script>
