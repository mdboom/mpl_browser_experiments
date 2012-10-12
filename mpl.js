function GUID () {
    var S4 = function ()
    {
        return Math.floor(
            Math.random() * 0x10000 /* 65536 */
        ).toString(16);
    };

    return (
        S4() + S4() + "-" +
            S4() + "-" +
            S4() + "-" +
            S4() + "-" +
            S4() + S4() + S4()
    );
};

window.onload = function() {
    if (!("WebSocket" in window)) {
        alert("WebSocket not supported");
        return;
    }
    var message = document.getElementById("message");

    control_ws = new WebSocket("ws://localhost:8888/event");
    control_ws.onmessage = function (evt) {
        var msg = JSON.parse(evt.data);
        message.textContent = msg[0];
    };

    var canvas = document.getElementById("myCanvas");
    var context = canvas.getContext("2d");
    imageObj = new Image();
    imageObj.onload = function() {
        context.drawImage(imageObj, 0, 0);
    };

    var image_ws = new WebSocket("ws://localhost:8888/image");
    image_ws.parts = []
    image_ws.onopen = function() {image_ws.send(1)};
    image_ws.onmessage = function (evt) {
        imageObj.src = (window.URL || window.webkitURL).createObjectURL(evt.data);
    }
};

function mouse_event(event, name) {
    control_ws.send(JSON.stringify({type: name, x: event.clientX, y: event.clientY, button: event.button}));
}
