# -*- coding: utf-8 -*-
import logging

from threading import Thread

from .models import User, UserAlert
from .utils import get_args, get_pokemon_name, get_pokemon_id
import telepot
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardHide

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
        
        markup_location = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text='Enviar localização', request_location=True)],
        ], resize_keyboard=True)
        
        markup_hide = ReplyKeyboardHide(hide_keyboard=True)
        
        log.info('New message from %ld', chat_id)
        
        user, created = User.get_or_create(chat_id=chat_id)
        
        if 'text' in message:
            if message['text'] == '/enable':
                user.enabled = False
                user.save()
                self.telegram_bot.sendMessage(chat_id, 'Notificações ativadas. Envie sua localização.', reply_markup=markup_location)
            elif message['text'] == '/disable':
                user.enabled = False
                user.save()
                self.telegram_bot.sendMessage(chat_id, 'Notificações desativadas.', reply_markup=markup_hide)
            elif message['text'] == '/catchable':
                user.report_catchable = not user.report_catchable
                user.save()
                
                if user.report_catchable:
                    self.telegram_bot.sendMessage(chat_id, 'Você só será notificado de Pokémon na sua lista.')
                else:
                    self.telegram_bot.sendMessage(chat_id, 'Você será notificado de todos os Pokémon próximos.')
            elif message['text'] == '/list':
                text = ''
                
                query = (UserAlert
                        .select()
                        .where(UserAlert.user == user)
                        .order_by(UserAlert.pokemon_id))
                
                pokemons = [p.pokemon_id for p in query]
                
                if len(pokemons) == 0:
                    text = 'Nenhum Pokémon encontrado.'
                else:
                    text = 'Você receberá notificações dos seguintes Pokémons:\n\n'
                for p in pokemons:
                    text += '#{} - {}\n'.format(p, get_pokemon_name(p))
                
                
                    
                self.telegram_bot.sendMessage(chat_id, text)
            elif message['text'][:4] == '/add':
                arg = message['text'][4:].strip()
                text = ''
                
                pokemon_id = None
                
                if arg.isdigit():
                    pokemon_id = int(arg)
                    
                    if not (1 <= pokemon_id <= 151):
                        pokemon_id = None
                else:
                    pokemon_id = get_pokemon_id(arg)
                    
                if pokemon_id != None:
                    try:
                        UserAlert.create(user=user, pokemon_id=pokemon_id)
                    except IntegrityError:
                        pass
                        
                    text = '#{} - {} adicionado.'.format(pokemon_id, get_pokemon_name(pokemon_id))
                else:
                    if arg != None and arg != '':
                        text = '\'{}\' não corresponde a nenhum Pokémon.'.format(arg)
                    else:
                        text = 'Comando inválido.'
                        
                self.telegram_bot.sendMessage(chat_id, text)
            elif message['text'][:4] == '/del':
                arg = message['text'][4:].strip()
                text = ''
                
                pokemon_id = None
                
                if arg.isdigit():
                    pokemon_id = int(arg)
                    
                    if not (1 <= pokemon_id <= 151):
                        pokemon_id = None
                else:
                    pokemon_id = get_pokemon_id(arg)
                    
                if pokemon_id != None:
                    query = (UserAlert
                            .delete()
                            .where((UserAlert.user == user) &
                                   (UserAlert.pokemon_id == pokemon_id)))
                    
                    if query.execute() == 0:
                        text = '#{} - {} não estava na sua lista.'.format(pokemon_id, get_pokemon_name(pokemon_id))
                    else:
                        text = '#{} - {} removido.'.format(pokemon_id, get_pokemon_name(pokemon_id))
                else:
                    if arg != None and arg != '':
                        text = '\'{}\' não corresponde a nenhum Pokémon.'.format(arg)
                    else:
                        text = 'Comando inválido.'
                    
                self.telegram_bot.sendMessage(chat_id, text)
            else:
                text = ''
                if message['text'] != '/help':
                    text += 'Comando não reconhecido.\n\n'
                text += '**Comandos disponívels**\n\n'
                text += '/enable : Ativar notificações.\n'
                text += '/disable : Desativar notificações.\n'
                text += '/list : Pokémons ativados.\n'
                text += '/add <nome> : Adicionar Pokémon.\n'
                text += '/del <nome> : Remover Pokémon.\n'
                text += '/help : Mostra essa mensagem.'
                
                self.telegram_bot.sendMessage(chat_id, text, parse_mode='Markdown')
        
        if 'location' in message:
            text = 'Localização atualizada.'
        
            user.latitude = message['location']['latitude']
            user.longitude = message['location']['longitude']
            
            if user.enabled == False:
                user.enabled = True
                text += '\nVocê receberá notificações.'
            
            user.save()
            
            self.telegram_bot.sendMessage(chat_id, text, reply_markup=markup_location)