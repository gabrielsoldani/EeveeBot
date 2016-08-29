# -*- coding: utf-8 -*-
import logging
import os
import sys
import time

from datetime import datetime

import configargparse
import googlemaps
from googlemaps.exceptions import ApiError, HTTPError, Timeout, TransportError
import geopy.distance

log = logging.getLogger(__name__)
     
def memoize(function):
    memo = {}

    def wrapper(*args):
        if args in memo:
            return memo[args]
        else:
            rv = function(*args)
            memo[args] = rv
            return rv
    return wrapper

@memoize    
def get_args():
    def parse_unicode(bytestring):
        decoded_string = bytestring.decode(sys.getfilesystemencoding())
        return decoded_string
        
    configpath = os.path.join(os.path.dirname(__file__), '../config/config.ini')
    parser = configargparse.ArgParser(default_config_files=[configpath], auto_env_var_prefix='EEVEEBOT_')
    parser.add_argument('-k', '--telegram-key', required=True,
                        help='Telegram Key')
    parser.add_argument('-H', '--host', default='127.0.0.1',
                        help='Set web server listening host')
    parser.add_argument('-P', '--port', type=int, default=5000,
                        help='Set web server listening port')
    parser.add_argument('-t', '--token',
                        help='Set web hook authentication token')
    parser.add_argument('--db', default='eeveebot.db', metavar='filename.db',
                        help='SQLite database filename (default: eeveebot.db)')
    parser.add_argument('--db-type', default='sqlite',
                        help='Type of database to be used (default: sqlite)')
    parser.add_argument('--db-name',
                        help='Name of the database to be used')
    parser.add_argument('--db-user', metavar='username',
                        help='Username for the database')
    parser.add_argument('--db-pass', metavar='password',
                        help='Password for the database')
    parser.add_argument('--db-host',
                        help='IP or hostname for the database')
    parser.add_argument('--db-port', type=int, default=3306,
                        help='Port for the database')
    parser.add_argument('--db-max-connections', type=int, default=5,
                        help='Max connections (per thread) for the database')
    parser.add_argument('-v', '--verbose', nargs='?', const='nofile', default=False, metavar='filename.log',
                        help='Show debug messages.')
    parser.set_defaults(DEBUG=False)
    
    args = parser.parse_args()
    
    return args
    
def get_new_coords(init_loc, distance, bearing):
    """
    Given an initial lat/lng, a distance (in meters), and a bearing (degrees),
    this will calculate the resulting lat/lng coordinates.
    """
    origin = geopy.Point(init_loc[0], init_loc[1])
    destination = geopy.distance.distance(meters=distance).destination(origin, bearing)
    return (destination.latitude, destination.longitude)
    
def get_outer_square(center, radius):
    top_center = get_new_coords(center, radius, 90)
    top_left = get_new_coords(top_center, radius, 180)
    bottom_center = get_new_coords(center, radius, 270)
    bottom_right = get_new_coords(bottom_center, radius, 0)
    
    return {
        'min_latitude': top_left[0],
        'max_latitude': bottom_right[0],
        'min_longitude': bottom_right[1],
        'max_longitude': top_left[1]
    }
    
def get_distance(a, b):
    return geopy.distance.distance(a, b).meters
    
def format_time_left(s):
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    
    return '%dm %ds' % (m, s)
    
pokemon_names = {
    "1": "Bulbasaur",
    "2": "Ivysaur",
    "3": "Venusaur",
    "4": "Charmander",
    "5": "Charmeleon",
    "6": "Charizard",
    "7": "Squirtle",
    "8": "Wartortle",
    "9": "Blastoise",
    "10": "Caterpie",
    "11": "Metapod",
    "12": "Butterfree",
    "13": "Weedle",
    "14": "Kakuna",
    "15": "Beedrill",
    "16": "Pidgey",
    "17": "Pidgeotto",
    "18": "Pidgeot",
    "19": "Rattata",
    "20": "Raticate",
    "21": "Spearow",
    "22": "Fearow",
    "23": "Ekans",
    "24": "Arbok",
    "25": "Pikachu",
    "26": "Raichu",
    "27": "Sandshrew",
    "28": "Sandslash",
    "29": "Nidoran♀",
    "30": "Nidorina",
    "31": "Nidoqueen",
    "32": "Nidoran♂",
    "33": "Nidorino",
    "34": "Nidoking",
    "35": "Clefairy",
    "36": "Clefable",
    "37": "Vulpix",
    "38": "Ninetales",
    "39": "Jigglypuff",
    "40": "Wigglytuff",
    "41": "Zubat",
    "42": "Golbat",
    "43": "Oddish",
    "44": "Gloom",
    "45": "Vileplume",
    "46": "Paras",
    "47": "Parasect",
    "48": "Venonat",
    "49": "Venomoth",
    "50": "Diglett",
    "51": "Dugtrio",
    "52": "Meowth",
    "53": "Persian",
    "54": "Psyduck",
    "55": "Golduck",
    "56": "Mankey",
    "57": "Primeape",
    "58": "Growlithe",
    "59": "Arcanine",
    "60": "Poliwag",
    "61": "Poliwhirl",
    "62": "Poliwrath",
    "63": "Abra",
    "64": "Kadabra",
    "65": "Alakazam",
    "66": "Machop",
    "67": "Machoke",
    "68": "Machamp",
    "69": "Bellsprout",
    "70": "Weepinbell",
    "71": "Victreebel",
    "72": "Tentacool",
    "73": "Tentacruel",
    "74": "Geodude",
    "75": "Graveler",
    "76": "Golem",
    "77": "Ponyta",
    "78": "Rapidash",
    "79": "Slowpoke",
    "80": "Slowbro",
    "81": "Magnemite",
    "82": "Magneton",
    "83": "Farfetch'd",
    "84": "Doduo",
    "85": "Dodrio",
    "86": "Seel",
    "87": "Dewgong",
    "88": "Grimer",
    "89": "Muk",
    "90": "Shellder",
    "91": "Cloyster",
    "92": "Gastly",
    "93": "Haunter",
    "94": "Gengar",
    "95": "Onix",
    "96": "Drowzee",
    "97": "Hypno",
    "98": "Krabby",
    "99": "Kingler",
    "100": "Voltorb",
    "101": "Electrode",
    "102": "Exeggcute",
    "103": "Exeggutor",
    "104": "Cubone",
    "105": "Marowak",
    "106": "Hitmonlee",
    "107": "Hitmonchan",
    "108": "Lickitung",
    "109": "Koffing",
    "110": "Weezing",
    "111": "Rhyhorn",
    "112": "Rhydon",
    "113": "Chansey",
    "114": "Tangela",
    "115": "Kangaskhan",
    "116": "Horsea",
    "117": "Seadra",
    "118": "Goldeen",
    "119": "Seaking",
    "120": "Staryu",
    "121": "Starmie",
    "122": "Mr. Mime",
    "123": "Scyther",
    "124": "Jynx",
    "125": "Electabuzz",
    "126": "Magmar",
    "127": "Pinsir",
    "128": "Tauros",
    "129": "Magikarp",
    "130": "Gyarados",
    "131": "Lapras",
    "132": "Ditto",
    "133": "Eevee",
    "134": "Vaporeon",
    "135": "Jolteon",
    "136": "Flareon",
    "137": "Porygon",
    "138": "Omanyte",
    "139": "Omastar",
    "140": "Kabuto",
    "141": "Kabutops",
    "142": "Aerodactyl",
    "143": "Snorlax",
    "144": "Articuno",
    "145": "Zapdos",
    "146": "Moltres",
    "147": "Dratini",
    "148": "Dragonair",
    "149": "Dragonite",
    "150": "Mewtwo",
    "151": "Mew"
}
    
def get_pokemon_name(pokemon_id):
    return pokemon_names.get(str(pokemon_id), 'Unknown')