import datetime

import flask
from flask import Flask
from redislite import Redis

app = Flask(__name__)
red = Redis('./redis.db')


def format_sse(data: str, event=None) -> str:
    msg = f'data: {data}\n\n'
    if event is not None:
        msg = f'event: {event}\n{msg}'
    return msg


def event_stream():
    pubsub = red.pubsub()
    pubsub.subscribe('installation_progress')
    for message in pubsub.listen():
        print(message)
        yield format_sse(message['data'], 'installation_progress')


@app.route('/post')
def post():
    message = flask.request.args['message']
    user = flask.session.get('user', 'anonymous')
    now = datetime.datetime.now().replace(microsecond=0).time()
    red.publish('installation_progress', u'[%s] %s: %s' % (now.isoformat(), user, message))
    return "1", 200


@app.route('/stream')
def stream():
    return flask.Response(event_stream(),
                          mimetype="text/event-stream")


@app.route('/sse_test')
def sse_test():
    return flask.render_template("sse_test.html")


if __name__ == '__main__':
    app.run(debug=True, port=5002, host="0.0.0.0")
