import json
import time
import datetime
import tornado.web
import tornado.ioloop
import tornado.websocket

import numpy as np

import matplotlib
matplotlib.use('Agg')

from matplotlib import _png
from matplotlib import backend_bases
from matplotlib.backends import backend_agg

import cStringIO

if [int(x) for x in matplotlib.__version__.split('.')[:2]] >= [1, 2]:
    def get_buffer(ren):
        return ren.buffer_rgba()
else:
    def get_buffer(ren):
        return ren.buffer_rgba(0, 0)


html = """
<html>
<head>
<script src="static/mpl.js"></script>
<body>
<canvas id="myCanvas" width="800" height="600"
   onmousedown="mouse_event(event, 'button_press')"
   onmouseup="mouse_event(event, 'button_release')"
   onmousemove="mouse_event(event, 'motion_notify')">
   </canvas>
   <div id="message">MESSAGE</div>
</body>
</html>
"""


class IndexPage(tornado.web.RequestHandler):
    def get(self):
        self.write(html)


class Timer(backend_bases.TimerBase):
    def _timer_start(self):
        self.timer = tornado.ioloop.PeriodicCallback(
            self._on_timer,
            self.interval)
        self.timer.start()

    def _timer_stop(self):
        self.timer.stop()
        self.timer = None


backend_bases.TimerBase = Timer


def serve_figure(fig, port=8888):
    image_sockets = set()

    # The panning and zooming is handled by the toolbar, (strange enough),
    # so we need to create a dummy one.
    class Toolbar(backend_bases.NavigationToolbar2):
        def _init_toolbar(self):
            self.message = ''
            self.pending = None

        def set_message(self, message):
            self.message = message

        def set_cursor(self, cursor):
            self.cursor = cursor

        def dynamic_update(self):
            if self.pending is None:
                ioloop = tornado.ioloop.IOLoop.instance()
                self.pending = ioloop.add_timeout(
                    datetime.timedelta(milliseconds=50),
                    self.update_callback)

        def update_callback(self):
            fig.canvas.draw()

        def refresh_all(self):
            diff.refresh()
            for image_socket in image_sockets:
                image_socket.refresh()
            self.pending = None

    toolbar = Toolbar(fig.canvas)
    toolbar.dynamic_update()

    _draw = backend_agg.FigureCanvasAgg.draw
    def draw(self):
        _draw(self)
        self.toolbar.refresh_all()
    backend_agg.FigureCanvasAgg.draw = draw
    backend_agg.FigureCanvasAgg.draw_idle = draw

    # Set pan mode -- it's the most interesting one
    toolbar.pan()

    class DiffBuffer:
        def __init__(self):
            self.last_buffer = None
            self.png_buffer = cStringIO.StringIO()

        def refresh(self):
            renderer = fig.canvas.get_renderer()
            buffer = np.array(
                np.frombuffer(get_buffer(renderer), dtype=np.uint32),
                copy=True)
            buffer = buffer.reshape((renderer.height, renderer.width))

            if self.last_buffer is not None:
                diff = buffer != self.last_buffer
                if not np.any(diff):
                    output = np.zeros((1, 1))
                else:
                    output = np.where(diff, buffer, 0)
            else:
                output = buffer

            self.png_buffer.reset()
            self.png_buffer.truncate()
            _png.write_png(output.tostring(),
                           output.shape[1], output.shape[0],
                           self.png_buffer)

            self.last_buffer = buffer

        def get(self):
            return self.png_buffer.getvalue()

    diff = DiffBuffer()

    class Image(tornado.websocket.WebSocketHandler):
        def open(self):
            self.last_buffer = None
            image_sockets.add(self)
            self.init = True

        def on_message(self, message):
            diff.last_buffer = None
            diff.refresh()
            self.refresh()

        def on_close(self):
            self.init = False
            image_sockets.remove(self)

        def refresh(self):
            if not self.init:
                return

            self.write_message(diff.get(), binary=True)

    class Event(tornado.websocket.WebSocketHandler):
        def open(self):
            self.pending = None

        def on_message(self, message):
            message = json.loads(message)
            type = message['type']
            if type != 'poll':
                x = int(message['x'])
                y = int(message['y'])
                y = fig.canvas.get_renderer().height - y

                # Javascript button numbers and matplotlib button numbers are
                # off by 1
                button = int(message['button']) + 1

                # The right mouse button pops up a context menu, which doesn't
                # work very well, so use the middle mouse button instead
                if button == 2:
                    button = 3

                if type == 'button_press':
                    fig.canvas.button_press_event(x, y, button)
                elif type == 'button_release':
                    fig.canvas.button_release_event(x, y, button)
                elif type == 'motion_notify':
                    fig.canvas.motion_notify_event(x, y)

            self.write_message(
                json.dumps(
                    {'message': fig.canvas.toolbar.message,
                     'cursor': fig.canvas.toolbar.cursor}))

        def on_close(self):
            pass

    application = tornado.web.Application([
        (r"/", IndexPage),
        (r"/image", Image),
        (r"/event", Event),
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': '.'}),
    ])

    application.listen(port)
    tornado.ioloop.IOLoop.instance().start()


class Timer(object):
    def __init__(self, name="", reset=False):
        self.start = time.time()
        self.name = name
        self.reset = reset

    def __call__(self, reset=None):
        if reset is None:
            reset = self.reset
        old_time = self.start
        new_time = time.time()
        if reset:
            self.start = new_time
        return new_time - old_time

    def __repr__(self):
        return str(self.name)+" %s ms"%(int(self()*1000))


global_timer = Timer("Global timer", reset=True)
