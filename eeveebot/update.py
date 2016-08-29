from datetime import datetime
import logging

from threading import Thread

from .utils import get_args, get_outer_square, get_pokemon_name, format_time_left
from .models import User, UserAlert, Location

log = logging.getLogger(__name__)

class UpdateThread(Thread):
    def __init__(self, app):
        super(UpdateThread, self).__init__()
        self.app = app
        self.queue = app.update_queue

    def run(self):
        while True:
            try:
                # Loop the queue
                while True:
                    message_type, message = self.queue.get()
                    
                    log.info('New message!')
                    log.info(message)
                    
                    if message_type == 'pokemon':
                        if ('pokemon_id' not in message or
                            'encounter_id' not in message or
                            'disappear_time' not in message or
                            'latitude' not in message or
                            'longitude' not in message):
                            log.debug('Invalid pokemon message. Ignoring.')
                        else:
                            self.trigger_pokemon(message)
                    
                    if self.queue.qsize() > 50:
                        log.warning('Update queue is > 50 (@%d); try increasing --update-threads', self.queue.qsize())
                    
                    self.queue.task_done()
            except KeyboardInterrupt:
                break
            except Exception as e:
                log.exception('Exception in UpdateThread: %s', e)
                
    def trigger_pokemon(self, message):   
        self.app.seen_lock.acquire()
        try:
            if self.app.seen.get(message['encounter_id']):
                return
        
            self.app.seen[message['encounter_id']] = True
        finally:
            self.app.seen_lock.release()
        
        dissapear_time = datetime.utcfromtimestamp(message['disappear_time'])      
        pokemon_id = message['pokemon_id']
        latitude = message['latitude']
        longitude = message['longitude']
        
        box = get_outer_square((latitude, longitude), 70)
        
        query = (User
                 .select(User)
                 #.join(UserAlert)
                 .where(
                    (User.enabled == True) &
                    #(UserAlert.pokemon_id == pokemon_id) &
                    ((User.latitude >= box['min_latitude']) &
                     (User.latitude <= box['max_latitude']) &
                     (User.longitude >= box['min_longitude']) &
                     (User.longitude <= box['max_longitude']))))
                
        chats = [user.chat_id for user in query]
        
        if len(chats) == 0:
            print 'No users found.'
            print box
            
        seconds_left = (dissapear_time - datetime.utcnow()).total_seconds()

        location, created = Location.get_or_create(latitude=latitude, longitude=longitude)

        alarm = {
            'title': '%s apareceu! (%s restantes)' % (get_pokemon_name(pokemon_id), format_time_left(seconds_left)),
            'address': '%f, %f' % (latitude, longitude),
            'latitude': latitude,
            'longitude': longitude,
        }
        
        if location.resolved == True:
            alarm['address'] = '%s, %s' % (location.street_name, location.street_number)
        
        self.app.alarm_queue.put((chats, alarm))
        