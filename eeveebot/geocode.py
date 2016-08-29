from .utils import get_args
from .models import Location

import googlemaps

args = get_args()

gmaps = googlemaps.Client('AIzaSyBJ96plsNpdAmpc1u-fa1P7bUgDALGDhoA')

def get_location(position):
    latitude = position[0]
    longitude = position[1]

    location, created = Location.get_or_create(latitude=latitude, longitude=longitude)
    
    if location.resolved:
        return location
    
    try:
        result = gmaps.reverse_geocode((location.latitude, location.longitude), language='pt-BR')
    except:
        return location
    
    if len(result) == 0:
        return location
        
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
    
    return location