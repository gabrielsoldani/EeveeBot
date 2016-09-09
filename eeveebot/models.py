import logging

from datetime import datetime

from peewee import SqliteDatabase, Model, DoubleField, BooleanField, CharField, SmallIntegerField, BigIntegerField, DateTimeField, ForeignKeyField, CompositeKey, Proxy
from playhouse.flask_utils import FlaskDB
from playhouse.pool import PooledMySQLDatabase
from playhouse.shortcuts import RetryOperationalError

from . import config
from .utils import get_args

log = logging.getLogger(__name__)

args = get_args()
flaskDb = FlaskDB()

class MyRetryDB(RetryOperationalError, PooledMySQLDatabase):
    pass
    
def init_database(app):
    if args.db_type == 'mysql':
        log.info('Connecting to MySQL database on %s:%i', args.db_host, args.db_port)
        connections = args.db_max_connections
        db = MyRetryDB(
            args.db_name,
            user=args.db_user,
            password=args.db_pass,
            host=args.db_host,
            port=args.db_port,
            max_connections=connections,
            stale_timeout=300)
    else:
        log.info('Connecting to local SQLite database')
        db = SqliteDatabase(args.db)
        
    app.config['DATABASE'] = db
    flaskDb.init_app(app)
    
    return db
    
def create_tables(db):
    db.connect()
    db.create_tables([Location, User, UserAlert], safe=True)
    db.close()

class BaseModel(flaskDb.Model):
    pass

class Location(BaseModel):
    latitude = DoubleField()
    longitude = DoubleField()
    
    resolved = BooleanField(index=True, default=False)
    
    street_name = CharField(null=True)
    street_number = CharField(null=True)
    sublocality = CharField(null=True)
    locality = CharField(null=True)
    premise = CharField(null=True)
    
    
    class Meta:
        primary_key = CompositeKey('latitude', 'longitude')
        
class User(BaseModel):
    chat_id = BigIntegerField(primary_key=True)
    latitude = DoubleField(null=True)
    longitude = DoubleField(null=True)
    enabled = BooleanField(default=False, index=True)
    report_catchable = BooleanField(default=False, index=True)
    last_message = DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = ((('latitude', 'longitude'), False),)
    
class UserAlert(BaseModel):
    user = ForeignKeyField(User)
    pokemon_id = SmallIntegerField()
    
    class Meta:
        primary_key = CompositeKey('user', 'pokemon_id')