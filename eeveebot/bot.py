# -*- coding: utf-8 -*-
import logging

from threading import Thread

from .models import User, UserAlert
from .utils import get_args
import telepot

log = logging.getLogger(__name__)

args = get_args()

class BotThread(Thread):
    def __init__(self, app):
        super(BotThread, self).__init__()
        self.app = app
        self.telegram_bot = telepot.Bot(args.telegram_key)
        
    def run(self):
        while True:
            try:
                self.telegram_bot.message_loop(callback=self.on_message, run_forever=True)
            except KeyboardInterrupt:
                break
            except Exception as e:
                log.exception('Exception in BotThread: %s', e)
                
    def on_message(self, message):       
        chat_id = message['chat']['id']
        
        log.info('New message from %ld', chat_id)
        
        user, created = User.get_or_create(chat_id=chat_id)
        
        if created:
            self.telegram_bot.sendMessage(chat_id, 'Olá! Eu sou o Eevee Robot e eu posso te notificar dos Pokémons próximos!')
        
        if 'location' in message:
            user.latitude = message['location']['latitude']
            user.longitude = message['location']['longitude']
            user.enabled = True
            user.save()
            
            self.telegram_bot.sendMessage(chat_id, 'Localização atualizada. Assim que aparecer algum Pokémon, eu vou te avisar :)')