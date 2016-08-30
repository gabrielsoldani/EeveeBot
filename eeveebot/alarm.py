import logging

from threading import Thread

from .utils import get_args
import telepot

log = logging.getLogger(__name__)

args = get_args()

class AlarmThread(Thread):
    def __init__(self, app):
        super(AlarmThread, self).__init__()
        self.app = app
        self.queue = app.alarm_queue
        self.telegram_bot = telepot.Bot(args.telegram_key)

    def run(self):
        while True:
            try:
                # Loop the queue
                while True:
                    chats, method, args = self.queue.get()
                                       
                    self.bulk_send(chats, method, args)
                    
                    if self.queue.qsize() > 50:
                        log.warning('Alarm queue is > 50 (@%d); try increasing --alarm-threads', self.queue.qsize())
                    
                    self.queue.task_done()
            except KeyboardInterrupt:
                break
            except Exception as e:
                log.exception('Exception in AlarmThread: %s', e)
                
    def bulk_send(self, chats, method, args):
        fn = None
        
        if hasattr(self.telegram_bot, method) == False:
            log.debug('Unsupported method %s', method)
            return
         
        fn = getattr(self.telegram_bot, method)
    
        for chat_id in chats:
            args['chat_id'] = chat_id
            fn(**args)