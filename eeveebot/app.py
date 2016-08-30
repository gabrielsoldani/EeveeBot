import logging

from Queue import Queue
from threading import Lock

from flask import Flask
from flask_compress import Compress

from . import config
from .utils import get_args

log = logging.getLogger(__name__)

compress = Compress()

args = get_args()

class EeveeBot(Flask):
    def __init__(self, import_name, **kwargs):
        super(EeveeBot, self).__init__(import_name, **kwargs)
        compress.init_app(self)
        
        self.seen = {}
        self.seen_lock = Lock()
        self.update_queue = Queue()
        self.alarm_queue = Queue()
        
        if args.token:
            self.route('/%s' % args.token, methods=['POST'])(self.post_update)
        else:
            self.route('/', methods=['POST'])(self.post_update)
            
        self.route('/test', methods=['GET'])(self.test)
        
        
    def post_update(self):
        print 'Received update!'
    
    def test(self):
        import datetime
        import time
            
        message = {
            'encounter_id': 'encounter_id',
            'pokemon_id': 132,
            'latitude': -22.931950,
            'longitude': -43.247290,
            'disappear_time': time.time() + 60+42
        }
        
        self.update_queue.put(('pokemon', message))
        
        return ('Hello', 200)