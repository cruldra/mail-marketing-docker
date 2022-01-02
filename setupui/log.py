import json
from datetime import datetime
from logging import StreamHandler


class SSEHandler(StreamHandler):

    def __init__(self, redis, topic):
        StreamHandler.__init__(self)
        self.redis = redis
        self.topic = topic

    def emit(self, record):
        def get_level_color():
            return {
                40: "red",
                30: "yellow",
                20: "green"
            }.get(record.levelno)

        self.redis.publish(self.topic, json.dumps({
            "level": record.levelname,
            "msg": record.msg,
            "time": datetime.now().strftime('%H:%M:%S'),
            "color": get_level_color()
        }))
