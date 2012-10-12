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

import cStringIO
png_buffer = cStringIO.StringIO()

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


image_socket = None
def serve_figure(fig, port=8888):
    # The panning and zooming is handled by the toolbar, (strange enough),
    # so we need to create a dummy one.
    class Toolbar(backend_bases.NavigationToolbar2):
        def _init_toolbar(self):
            self.message = ''
            self.needs_draw = True

        def set_message(self, message):
            self.message = message

        def dynamic_update(self):
            if self.needs_draw is False:
                Image.image_number += 1
            self.needs_draw = True

    toolbar = Toolbar(fig.canvas)

    # Set pan mode -- it's the most interesting one
    toolbar.pan()

    def RateLimited(maxPerSecond):
        "Based on http://stackoverflow.com/a/667706/1200039"
        min_time = 1.0 / float(maxPerSecond)
        def decorate(func):
            # these are lists so we can modify them below
            # sort of a poor-man's nonlocal keyword
            timeout = [0.0]
            pending = [False]
            def rateLimitedFunction(*args,**kwargs):
                # called with no pending calls: run function
                # called with with pending call: do nothing
                # called with no pending calls, but within the window of the last call: set timeout for pending call
                curr_time = time.time()
                if pending[0]:
                    return
                else:
                    def ff():
                        timeout[0] = time.time() + min_time
                        ret = func(*args, **kwargs)
                        pending[0] = False
                        return ret

                    ioloop = tornado.ioloop.IOLoop.instance()
                    pending[0] = ioloop.add_timeout(datetime.timedelta(seconds=max(0, timeout[0] - curr_time)), ff)
            return rateLimitedFunction
        return decorate

    class Image(tornado.websocket.WebSocketHandler):
        last_buffer = None
        image_number = 0
        def open(self):
            global image_socket
            image_socket = self
            self.init=True

        def on_message(self, message):
            self.refresh()

        def close(self):
            global image_socket
            self.init = False
            image_socket = None

        @RateLimited(5)
        def refresh(self):
            if not self.init: return
            if fig.canvas.toolbar.needs_draw:
                fig.canvas.draw()
                fig.canvas.toolbar.needs_draw = False
            renderer = fig.canvas.get_renderer()
            buffer = np.array(
                np.frombuffer(get_buffer(renderer), dtype=np.uint32),
                copy=True)
            buffer = buffer.reshape((renderer.height, renderer.width))

            last_buffer = self.last_buffer
            if last_buffer is not None:
                diff = buffer != last_buffer
                if not np.any(diff):
                    print "Empty"
                    output = np.zeros((1, 1))
                else:
                    print "Optimized"
                    output = np.where(diff, buffer, 0)
            else:
                print "Full"
                output = buffer

            png_buffer.reset()
            png_buffer.truncate()
            #global_timer()
            _png.write_png(output.tostring(),
                           output.shape[1], output.shape[0],
                           png_buffer)
            #print global_timer
            self.write_message(png_buffer.getvalue(), binary=True)
            self.last_buffer = buffer

    class Event(tornado.websocket.WebSocketHandler):
        def open(self):
            print "Opened Event connection"

        def on_message(self, message):
            global image_socket
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

            # The response is:
            #   [message (str), needs_draw (bool) ]
            self.write_message(
                json.dumps(
                    [fig.canvas.toolbar.message,
                     fig.canvas.toolbar.needs_draw]))

            if fig.canvas.toolbar.needs_draw:
                image_socket.refresh()

        def on_close(self):
            print "Event websocket closed"

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

global_timer=Timer("Global timer", reset=True)
