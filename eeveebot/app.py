import logging
import json

from Queue import Queue
from threading import Lock

from flask import Flask, request
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
        log.debug('POST request received from %s.' % (request.remote_addr))
        try:
            data = json.loads(request.data)
        except:
            return ('', 204)

        if ('message' in data and
            'type' in data):
            self.update_queue.put((data['type'], data['message']))
        
        return ('', 204)
    
    def test(self):
        import uuid
        import time
            
        message = {
            'encounter_id': uuid.uuid4(),
            'pokemon_id': 149,
            'latitude': -22.931950,
            'longitude': -43.247290,
            'disappear_time': time.time() + 60+42
        }
        
        self.update_queue.put(('pokemon', message))
        
        return ('Hello', 200)