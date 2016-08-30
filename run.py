import logging

logging.basicConfig(format='%(asctime)s [%(threadName)16s][%(module)14s][%(levelname)8s] %(message)s')
log = logging.getLogger()

from eeveebot.app import EeveeBot
from eeveebot.models import init_database, create_tables
from eeveebot.utils import get_args
from eeveebot.update import UpdateThread
from eeveebot.alarm import AlarmThread
from eeveebot.bot import BotThread
from eeveebot.geocoder import GeocoderThread

def main():
    args = get_args()
    
    # Add file logging if enabled
    if args.verbose and args.verbose != 'nofile':
        filelog = logging.FileHandler(args.verbose)
        filelog.setFormatter(logging.Formatter('%(asctime)s [%(threadName)16s][%(module)14s][%(levelname)8s] %(message)s'))
        logging.getLogger('').addHandler(filelog)
        
    if args.verbose:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    
    app = EeveeBot(__name__)

    db = init_database(app)
    create_tables(db)
    
    update_thread = UpdateThread(app)
    update_thread.daemon = True
    update_thread.start()
    
    alarm_thread = AlarmThread(app)
    alarm_thread.daemon = True
    alarm_thread.start()
    
    bot_thread = BotThread(app)
    bot_thread.daemon = True
    bot_thread.start()
    
    if args.gmaps_key:
        geocoder_thread = GeocoderThread(app)
        geocoder_thread.daemon = True
        geocoder_thread.start()
    else:
        log.debug('No --gmaps-key, geocoder will not be enabled.')
    
    if args.verbose:
        app.run(threaded=True, use_reloader=False, debug=True, host=args.host, port=args.port)
    else:
        app.run(threaded=True, use_reloader=False, debug=False, host=args.host, port=args.port)

if __name__ == '__main__':
    main()
    