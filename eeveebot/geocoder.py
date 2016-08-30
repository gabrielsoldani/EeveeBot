import logging
import time

from threading import Thread

from .utils import get_args
from .models import Location

import googlemaps

log = logging.getLogger(__name__)

args = get_args()

class GeocoderThread(Thread):
    def __init__(self, app):
        super(GeocoderThread, self).__init__()
        self.app = app
        self.gmaps = googlemaps.Client(args.gmaps_key)
        
    def run(self):
        while True:
            try:
                query = (Location
                        .select()
                        .where(Location.resolved == False)
                        .limit(50))

                try:
                    for location in query:
                        self.geocode(location)
                        log.info('Successfully geocoded (%f, %f)', location.latitude, location.longitude)
                except Exception as e:
                    log.exception('Geocoding exception %s. Sleeping for 60 seconds.', e)
                    time.sleep(60)
                    
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                log.exception('Exception in GeocoderThread: %s', e)
                
    def geocode(self, location):
        result = self.gmaps.reverse_geocode((location.latitude, location.longitude), language='pt-BR')
        
        # Google doesn't know...
        if len(result) == 0:
            location.resolved = True
            location.save()
            
        result = result[0]
        
        for component in result['address_components']:
            if 'route' in component['types']:
                location.street_name = component['short_name']
            if 'street_number' in component['types']:
                location.street_number = component['short_name']
            if 'sublocality' in component['types'] and 'sublocality_level_1' in component['types']:
                location.sublocality = component['short_name']
            if 'locality' in component['types']:
                location.locality = component['short_name']
            if 'premise' in component['types']:
                location.premise = component['short_name']
                
        location.resolved = True
        location.save()
