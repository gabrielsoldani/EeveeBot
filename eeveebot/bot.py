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
        
        self.routes = {
            '/enable': self.on_enable,
            '/disable': self.on_disable,
            '/catchable': self.on_catchable,
            '/start': self.on_start,
            '/list': self.on_list,
            '/add': self.on_add,
            '/del': self.on_del,
            '/help': self.on_help
        }
        
        self.markup_location = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text='Enviar localização', request_location=True)],
        ], resize_keyboard=True)
        
        self.markup_hide = ReplyKeyboardHide(hide_keyboard=True)
        
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
        
        if created == True:
            self.add_default_pokemon(user)
            
        if 'text' in message and len(message['text']) > 0:
            args = message['text'].split()
            
            command = args[0]
            args = args[1:]
            
            fn = self.routes.get(command)
            if fn:
                fn(user, command, *args)
            else:
                self.on_help(user, command, *args)
        
        if 'location' in message:
            self.on_location(user, message['location'])
            
    def on_enable(self, user, command, *args):
        user.enabled = True
        user.save()
        self.telegram_bot.sendMessage(user.chat_id, 'Notificações ativadas. Envie sua localização.', reply_markup=self.markup_location)
        
    def on_disable(self, user, command, *args):
        user.enabled = False
        user.save()
        self.telegram_bot.sendMessage(user.chat_id, 'Notificações desativadas.', reply_markup=self.markup_hide)
    
    def on_catchable(self, user, command, *args):
        user.report_catchable = not user.report_catchable
        user.save()
        
        if user.report_catchable:
            self.telegram_bot.sendMessage(user.chat_id, 'Você será notificado de todos os Pokémon próximos.')
        else:
            self.telegram_bot.sendMessage(user.chat_id, 'Você só será notificado dos Pokemón na sua lista.')
            
    def on_list(self, user, command, *args):
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

        self.telegram_bot.sendMessage(user.chat_id, text)
    
    def on_add(self, user, command, *args):
        if len(args) == 0:
            text = 'Comando inválido.\n\n'
            text += 'Uso:\n'
            text += '/add <nome ou # ou all>\n\n'
            text += 'Exemplo:\n'
            text += '/add Bulbasaur'
            self.telegram_bot.sendMessage(user.chat_id, text)
            return
            
        if 'all' in args:
            self.add_all_pokemon(user)
            text = 'Todos os Pokémons foram adicionados.'
            self.telegram_bot.sendMessage(user.chat_id, text)
            return
            
        text = ''
        
        for arg in args:
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
                
                text += '#{} - {} adicionado.\n'.format(pokemon_id, get_pokemon_name(pokemon_id))               
        
        self.telegram_bot.sendMessage(user.chat_id, text.strip())
        
    def on_del(self, user, command, *args):
        if len(args) == 0:
            text = 'Comando inválido.\n\n'
            text += 'Uso:\n'
            text += '/del <nome ou # ou all>\n\n'
            text += 'Exemplo:\n'
            text += '/del Bulbasaur'
            self.telegram_bot.sendMessage(user.chat_id, text)
            return
            
        if 'all' in args:
            query = (UserAlert
                    .delete()
                    .where(UserAlert.user == user))
            
            query.execute()
            
            text = 'Todos os Pokémons foram removidos.'
            self.telegram_bot.sendMessage(user.chat_id, text)
            return
            
        text = ''
        
        for arg in args:
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
                    text += '#{} - {} não estava na sua lista.\n'.format(pokemon_id, get_pokemon_name(pokemon_id))
                else:
                    text += '#{} - {} removido.\n'.format(pokemon_id, get_pokemon_name(pokemon_id))             
        
        self.telegram_bot.sendMessage(user.chat_id, text.strip())
    
    def on_start(self, user, command, *args):
        text = 'Olá. Eu sou o Eevee Robot, e eu posso te avisar se eu vir algum Pokémon raro.\n\n'
        text += 'Para começar a receber notificações, basta usar o comando /enable e, em seguida, enviar a sua localização.\n\n'
        text += 'Você pode ver os Pokémons que eu vou te alertar usando o comando /list, e você pode modificar essa lista usando os comandos /add e /del.\n\n'
        text += 'Ah, e eu também posso te alertar se tiver algum Pokémon bem do seu ladinho, pra você não precisar ficar com o jogo aberto. É só usar o comando /catchable.\n\n'
        text += 'Qualquer dúvida você pode usar o comando /help para saber mais sobre os comandos.'
        
        self.telegram_bot.sendMessage(user.chat_id, text)
        
    def on_help(self, user, command, *args):
        text = ''
        if command != '/help':
            text += 'Comando não reconhecido.\n\n'
        text += '**Comandos disponíveis**\n\n'
        text += '/help - mostrar essa mensagem de ajuda\n'
        text += '/enable - ativar notificações\n'
        text += '/disable - desativar notificações\n'
        text += '/list - mostrar pokémons\n'
        text += '/add <nome ou #> - adicionar pokémon\n'
        text += '/del <nome ou # ou all> - remover pokémon\n'
        text += '/catchable - ativar/desativar notificações de todos os pokémons alcançáveis\n'
        
        self.telegram_bot.sendMessage(user.chat_id, text, parse_mode='Markdown')
        
    def on_location(self, user, location):
        text = 'Localização atualizada.'
        
        user.latitude = location['latitude']
        user.longitude = location['longitude']
        
        if user.enabled == False:
            user.enabled = True
            text += '\nVocê receberá notificações.'
        
        user.save()
        
        self.telegram_bot.sendMessage(user.chat_id, text, reply_markup=self.markup_location)
            
    def add_all_pokemon(self, user):
        values = [{'user': user, 'pokemon_id': id} for id in range(1, 152)]
        
        query = (UserAlert
                .insert_many(values))
        
        query.execute()
     
    def add_default_pokemon(self, user):
        default_pokemon = [
            2, # Ivysaur
            3, # Venusaur
            5, # Charmeleon
            6, # Charizard
            8, # Wartortle
            9, # Blastoise
            12, # Butterfree
            15, # Beedril
            18, # Pidgeot
            22, # Fearow
            24, # Arbok
            26, # Raichu
            28, # Sandslash
            31, # Nidoqueen
            34, # Nidoking
            36, # Clefable
            38, # Ninetales
            40, # Wigglytuff
            44, # Gloom
            45, # Vileplume
            47, # Parasect
            49, # Venomoth
            51, # Dugtrio
            53, # Persian
            57, # Primeape
            59, # Arcanine
            62, # Poliwrath
            64, # Kadabra
            65, # Alakazam
            67, # Machoke
            68, # Machamp
            70, # Weepinbell
            71, # Victreebel
            75, # Graveler
            76, # Golem
            78, # Rapidash
            80, # Slowbro
            82, # Magneton
            87, # Dewgong
            88, # Grimer
            89, # Muk
            91, # Cloyster
            93, # Haunter
            94, # Gengar
            95, # Onix
            97, # Hypno
            99, # Kingler
            101, # Electrode
            103, # Exeggutor
            105, # Marowak
            106, # Hitmonlee
            107, # Hitmonchan
            108, # Lickitung
            110, # Weezing
            112, # Rhydon
            113, # Chansey
            117, # Seadra
            121, # Starmie
            123, # Scyther
            124, # Jynx
            125, # Electabuzz
            126, # Magmar
            130, # Gyarados
            131, # Lapras
            134, # Vaporeon
            135, # Jolteon
            136, # Flareon
            137, # Porygon
            139, # Omastar
            141, # Kabutops
            142, # Aerodactyl
            143, # Snorlax
            148, # Dragonair
            149 # Dragonite
        ]
        
        values = [{'user': user, 'pokemon_id': id} for id in default_pokemon]
        
        query = (UserAlert
                .insert_many(values))
        
        query.execute()