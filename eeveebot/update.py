from datetime import datetime
import logging

from threading import Thread

from peewee import IntegrityError

from .utils import get_args, get_outer_square, get_pokemon_name, format_time_left, get_distance
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
                for x in range(5000):
                    message_type, message = self.queue.get()
                    
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
                    
                # Clean up expired sightings
                log.info('Cleaning up expired sightings...')
                self.app.seen_lock.acquire()
                try:
                    for encounter_id in self.app.seen:
                        disappear_time = datetime.utcfromtimestamp(self.app.seen[encounter_id])
                        seconds_left = (disappear_time - datetime.utcnow()).total_seconds()
                        
                        if seconds_left <= 0:
                            self.app.seen.popitem()
                        else:
                            break
                finally:
                    self.app.seen_lock.release()
            except KeyboardInterrupt:
                break
            except Exception as e:
                log.exception('Exception in UpdateThread: %s', e)
                
    def trigger_pokemon(self, message):   
        self.app.seen_lock.acquire()
        try:
            if self.app.seen.get(message['encounter_id']):
                return
        
            self.app.seen[message['encounter_id']] = message['disappear_time']
        finally:
            self.app.seen_lock.release()
        
        disappear_time = datetime.utcfromtimestamp(message['disappear_time'])      
        pokemon_id = message['pokemon_id']
        latitude = message['latitude']
        longitude = message['longitude']
                   
        seconds_left = (disappear_time - datetime.utcnow()).total_seconds()
                
        if seconds_left <= 30:
            return

        location, created = Location.get_or_create(latitude=latitude, longitude=longitude)

        pokemon_event = {
            'pokemon_id': pokemon_id,
            'pokemon_name': get_pokemon_name(pokemon_id),
            'disappear_time': disappear_time,
            'time_left': format_time_left(seconds_left),
            'latitude': latitude,
            'longitude': longitude,
        }
        
        if location.resolved == True:
            pokemon_event['address'] = '%s, %s' % (location.street_name, location.street_number)
            pokemon_event['sublocality'] = location.sublocality
            pokemon_event['locality'] = location.locality
       
        self.process_pokemon_event(**pokemon_event)
        
    def process_pokemon_event(self, pokemon_id, pokemon_name, disappear_time, time_left, latitude, longitude, address=None, sublocality=None, locality=None):
        box = get_outer_square((latitude, longitude), 70)
        
        query = (User
                 .select(User)
                 .where(
                    (User.enabled == True) &
                    (User.report_catchable == True) &
                    ((User.latitude >= box['min_latitude']) &
                     (User.latitude <= box['max_latitude']) &
                     (User.longitude >= box['min_longitude']) &
                     (User.longitude <= box['max_longitude']))))
                     
        
        chats = [user.chat_id for user in query if get_distance((user.latitude, user.longitude), (latitude, longitude)) <= 70]
        
        chats_catchable = chats
        
        if len(chats) > 0:
            args = {
                'text': '<b>{} bem do seu lado!</b>\n{} restantes.'.format(pokemon_name, time_left),
                'parse_mode': 'HTML'
            }
            
            self.app.alarm_queue.put((chats, 'sendMessage', args))
            
            args = {
                'title': pokemon_name,
                'address': address or '',
                'latitude': latitude,
                'longitude': longitude,
                'disable_notification': 'True'
            }
            
            self.app.alarm_queue.put((chats, 'sendVenue', args))
    
        box = get_outer_square((latitude, longitude), 200)
        
        query = (User
                 .select(User)
                 .join(UserAlert)
                 .where(
                    (User.enabled == True) &
                    (UserAlert.pokemon_id == pokemon_id) &
                    ((User.latitude >= box['min_latitude']) &
                     (User.latitude <= box['max_latitude']) &
                     (User.longitude >= box['min_longitude']) &
                     (User.longitude <= box['max_longitude']))))
        
        chats = [user.chat_id for user in query if get_distance((user.latitude, user.longitude), (latitude, longitude)) <= 200]
        
        chats = [x for x in chats if x not in chats_catchable]
        
        if len(chats) > 0:
            args = {
                'text': '<b>{} encontrado!</b>\n{} restantes.'.format(pokemon_name, time_left),
                'parse_mode': 'HTML'
            }
            
            self.app.alarm_queue.put((chats, 'sendMessage', args))
        
            args = {
                'title': pokemon_name,
                'address': address or '',
                'latitude': latitude,
                'longitude': longitude,
                'disable_notification': 'True'
            }
            
            self.app.alarm_queue.put((chats, 'sendVenue', args))
