var control_ws;

window.onload = function() {
    if (!("WebSocket" in window)) {
        alert("WebSocket not supported");
        return;
    }
    var message = document.getElementById("message");
    var canvas = document.getElementById("canvas");

    control_ws = new WebSocket("ws://" + document.location.host + "/event");
    control_ws.onmessage = function (evt) {
        var msg = JSON.parse(evt.data);
        message.textContent = msg['message'];

        var cursor = msg['cursor']
        switch(cursor)
        {
            case 0:
                cursor = 'pointer';
                break;
            case 1:
                cursor = 'default';
                break;
            case 2:
                cursor = 'crosshair';
                break;
            case 3:
                cursor = 'move';
                break;
        }
        canvas.style.cursor = cursor;
    };

    var canvas = document.getElementById("myCanvas");
    var context = canvas.getContext("2d");
    imageObj = new Image();
    imageObj.onload = function() {
        context.drawImage(imageObj, 0, 0);
    };

    var image_ws = new WebSocket("ws://" + document.location.host + "/image");
    image_ws.onopen = function() {
        image_ws.send(1)
    };
    image_ws.onmessage = function (evt) {
        imageObj.src = (window.URL || window.webkitURL).createObjectURL(
            evt.data);
    }
};

function mouse_event(event, name) {
    control_ws.send(JSON.stringify(
        {type: name,
         x: event.clientX, y: event.clientY,
         button: event.button}));
}
