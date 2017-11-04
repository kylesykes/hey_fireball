# -*- coding: utf-8 -*-
"""
This module encapsulates interations with a storage mechanism
that holds informatoin such as user scores, remaining points
for user, etc.

The abstract class `Storage` defines the methods needed 
to interact with a storage mechanism. 

This module contains two `Storage` subclasses: redis and
inmemory. Additional subclasses can be made that allow 
the use of any appropriate storage mechanism (database,
flat-file, etc.)
"""
import os
import datetime


#####################
# API
#####################


class Storage():
    """Class that defines how module storage functions 
    interact with a storage provider.
    """
    def user_exists(self, user_id: str):
        """Return True if user_id is in storage."""
        pass

    def get_user_points_used(self, user_id: str):
        """Return number of points used or 0."""
        pass

    def add_user_points_used(self, user_id: str, num: int):
        """Add `num` to user's total used points.""" 
        pass

    def get_user_points_received(self, user_id: str):
        """Return number of points received or 0."""
        pass

    def add_user_points_received(self, user_id: str, num: int):
        """Add `num` to user's total received points."""
        pass

    def get_users_and_scores(self):
        """Return list of tuples (user_id, points_received)."""
        pass

class AzureTableStorage(Storage):
    """Implementation of `Storage` that uses Azure Table Service.
    
    Env Var:
        TABLE_ACCOUNT : table service account name
        TABLE_KEY : table service key
        TABLE_SAS : table service sas
        TABLE_NAME : name of the table
    Only one of TABLE_KEY or TABLE_SAS is needed.

    PartitionKey: date by day, or Total
    RowKey: username
    Fields:
        received: points received
        given: points given
        negative: negative points received
    """

    POINTS_USED = 'POINTS_USED'
    POINTS_RECEIVED = 'POINTS_RECEIVED'
    NEGATIVE_POINTS_USED = 'NEGATIVE_POINTS_USED'
    USERS_LIST_KEY = 'USERS_LIST'
    TOTAL = 'TOTAL'

    def __init__(self):
        super().__init__()
        # Check is Redis library is installed.
        try:
            import azure.storage.table
        except ImportError:
            raise Exception('azure storage table package not installed!')
        self._account_name = os.environ.get("ACCOUNT_NAME")
        self._account_key = os.environ.get("ACCOUNT_KEY")
        self._account_sas = os.environ.get("ACCOUNT_SAS")
        self._table_name = os.environ.get("TABLE_NAME")
        self._table_service = azure.storage.table.TableService(self._account_name,
                                                                self._account_key,
                                                                self._account_sas)
        
    def _create_user_entry(self, user_id: str):
        """Create new user entry and init fields."""
        self._table_service.insert_entity(self._table_name,
                                            {'PartitionKey':self.TOTAL,
                                            'RowKey': user_id,
                                            POINTS_RECEIVED: 0,
                                            POINTS_USED: 0,
                                            NEGATIVE_POINTS_USED: 0})
        self._table_service.insert_entity(self._table_name,
                                            {'PartitionKey':self._get_today(),
                                            'RowKey': user_id,
                                            POINTS_RECEIVED: 0,
                                            POINTS_USED: 0,
                                            NEGATIVE_POINTS_USED: 0})

    def user_exists(self, user_id: str):
        """Return True if user_id is in storage."""
        filter_query = "PartitionKey eq '{total}' and RowKey eq '{user_id}'".format(self.TOTAL, user_id)
        results = self._table_service.query_entities(self._table_name,
                                            filter=filter_query,
                                            select='RowKey')
        return len(list(results)) > 0

    def get_user_points_used(self, user_id: str):
        """Return number of points used today or 0."""
        return self._table_service.get_entity(self._table_name,
                                              partition_key=self._get_today(),
                                              row_key=user_id,
                                              select=self.POINTS_USED)

    def add_user_points_used(self, user_id: str, num: int):
        """Add `num` to user's total used points today."""
        points = self.get_user_points_used(user_id)
        new_points = points + num
        self._table_service.update_entity(self._table_name,
                                          entity=)

    def get_user_points_received(self, user_id: str):
        """Return number of points received or 0."""
        return int(self._redis.hget(user_id, self.POINTS_RECEIVED))

    def add_user_points_received(self, user_id: str, num: int):
        """Add `num` to user's total received points."""
        self._redis.hincrby(user_id, self.POINTS_RECEIVED, num)

    def get_users_and_scores(self):
        """Return list of tuples (user_id, points_received)."""
        users = self._redis.smembers(self.USERS_LIST_KEY)
        return [(user, self.get_user_points_received(user)) for user in users]

    @staticmethod
    def _get_today():
        """Return today's date as a string YYYY-MM-DD."""
        return datetime.datetime.today().strftime('%Y-%m-%d')


class RedisStorage(Storage):
    """Implementation of `Storage` that uses Redis.
    
    Redis server's URL should be in env var `REDIS_URL`.

    key: username
    value: hash(POINTS_USED, POINTS_RECEIVED)
    """

    POINTS_USED = 'POINTS_USED'
    POINTS_RECEIVED = 'POINTS_RECEIVED'
    USERS_LIST_KEY = 'USERS_LIST'

    def __init__(self):
        super().__init__()
        # Check is Redis library is installed.
        try:
            import redis
        except ImportError:
            raise Exception('Redis package not installed!')
        self._redis = redis.from_url(os.environ.get("REDIS_URL"))
        
    def _create_user_entry(self, user_id: str):
        """Create new user entry and init fields."""
        self._redis.hmset(user_id, {self.POINTS_USED:0, self.POINTS_RECEIVED:0})
        self._redis.sadd(self.USERS_LIST_KEY, user_id)

    def user_exists(self, user_id: str):
        """Return True if user_id is in storage."""
        return self._redis.exists(user_id)

    def get_user_points_used(self, user_id: str):
        """Return number of points used or 0."""
        return int(self._redis.hget(user_id, self.POINTS_USED))

    def add_user_points_used(self, user_id: str, num: int):
        """Add `num` to user's total used points."""
        self._redis.hincrby(user_id, self.POINTS_USED, num)

    def get_user_points_received(self, user_id: str):
        """Return number of points received or 0."""
        return int(self._redis.hget(user_id, self.POINTS_RECEIVED))

    def add_user_points_received(self, user_id: str, num: int):
        """Add `num` to user's total received points."""
        self._redis.hincrby(user_id, self.POINTS_RECEIVED, num)

    def get_users_and_scores(self):
        """Return list of tuples (user_id, points_received)."""
        users = self._redis.smembers(self.USERS_LIST_KEY)
        return [(user, self.get_user_points_received(user)) for user in users]


class InMemoryStorage(Storage):
    """Implementation of `Storage` that uses a dict in memory.
    """

    POINTS_USED = 'POINTS_USED'
    POINTS_RECEIVED = 'POINTS_RECEIVED'

    def __init__(self):
        super().__init__()
        # Check is Redis library is installed.
        self._data = dict()

    def user_exists(self, user_id: str):
        """Return True if user_id is in storage."""
        return user_id in self._data

    def get_user_points_used(self, user_id: str):
        """Return number of points used or 0."""
        return self._data[user_id].get(self.POINTS_USED, 0)

    def add_user_points_used(self, user_id: str, num: int):
        """Add `num` to user's total used points."""
        user_data = self._data.setdefault(user_id, {})
        user_data[self.POINTS_USED] = user_data.get(self.POINTS_USED, 0) + num

    def get_user_points_received(self, user_id: str):
        """Return number of points received or 0."""
        return self._data[user_id].get(self.POINTS_RECEIVED, 0)

    def add_user_points_received(self, user_id: str, num: int):
        """Add `num` to user's total received points."""
        user_data = self._data.setdefault(user_id, {})
        user_data[self.POINTS_RECEIVED] = user_data.get(self.POINTS_RECEIVED, 0) + num

    def get_users_and_scores(self):
        """Return list of tuples (user_id, points_received)."""
        return [(k, v[self.POINTS_RECEIVED]) for k,v in self._data.items()]