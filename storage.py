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

    Class is responsible for ensuring users exists when
    querying/updating user data.
    """
    ### Points used
    def get_user_points_used_total(self, user_id: str):
        """Return total number of points used or 0."""
        pass

    def get_user_points_used(self, user_id: str):
        """Return number of points used today or 0."""
        pass

    def add_user_points_used(self, user_id: str, num: int):
        """Add `num` to user's total and today's used points.""" 
        pass

    ### Points received
    def get_user_points_received_total(self, user_id: str):
        """Return total number of points received or 0."""
        pass

    def get_user_points_received(self, user_id: str):
        """Return number of points received today or 0."""
        pass

    def add_user_points_received(self, user_id: str, num: int):
        """Add `num` to user's total and today's received points."""
        pass

    def get_users_and_scores_total(self):
        """Return list of tuples (user_id, points_received_total)."""
        pass

class AzureTableStorage(Storage):
    """Implementation of `Storage` that uses Azure Table Service.
    
    Env Var:
        ACCOUNT_NAME : table service account name
        ACCOUNT_KEY : table service key
        ACCOUNT_SAS : table service sas
        TABLE_NAME : name of the table
    Only one of TABLE_KEY or TABLE_SAS is needed.

    PartitionKey: date by day, or Total
    RowKey: username
    Fields:
        received total: points received
        given total: points given
        negative total: negative points received
        received today: points received
        given today: points given
        negative today: negative points received

    The records in the TOTAL partition contain the total and the daily total
    for each user. When data is retrieved from the table, the user's record
    from the TOTAL partition is grabbed. The LAST_UPDATE field is compared 
    to today's date: if it matches, that record is used; if the date it old,
    a copy of the record is added to the table in the date partition and 
    the record in the Total partition is updated with zero's for today's 
    counts.
    This approach allows all of a user's info to be grabbed/updated in a 
    single call to the table, not separate calls for Total and Today. The
    downside is that the entire Total record must be grabbed each time 
    (you can't select a subset of fields), because you might have 
    """

    POINTS_USED_TOTAL = 'POINTS_USED_TOTAL'
    POINTS_RECEIVED_TOTAL = 'POINTS_RECEIVED_TOTAL'
    NEGATIVE_POINTS_USED_TOTAL = 'NEGATIVE_POINTS_USED_TOTAL'
    POINTS_USED_TODAY = 'POINTS_USED_TODAY'
    POINTS_RECEIVED_TODAY = 'POINTS_RECEIVED_TODAY'
    NEGATIVE_POINTS_USED_TODAY = 'NEGATIVE_POINTS_USED_TODAY'
    USERS_LIST = 'USERS_LIST'
    TOTAL_PARTITION = 'TOTAL'

    def __init__(self):
        super().__init__()
        # Check is Redis library is installed.
        try:
            import azure.storage.table
        except ImportError:
            raise Exception('azure storage table package not installed!')
        self._users = None
        self._account_name = os.environ.get("ACCOUNT_NAME")
        self._account_key = os.environ.get("ACCOUNT_KEY")
        self._account_sas = os.environ.get("ACCOUNT_SAS")
        self._table_name = os.environ.get("TABLE_NAME")
        self._table_service = azure.storage.table.TableService(account_name=self._account_name,
                                                                account_key=self._account_key,
                                                                sas_token=self._account_sas)

    ### Users
    def _create_user_entry(self, user_id: str):
        """Create new user entry and init fields."""
        self._table_service.insert_entity(self._table_name,
                                            {'PartitionKey':self.TOTAL_PARTITION,
                                            'RowKey': user_id,
                                            self.POINTS_RECEIVED_TOTAL: 0,
                                            self.POINTS_USED_TOTAL: 0,
                                            self.NEGATIVE_POINTS_USED_TOTAL: 0,
                                            self.POINTS_RECEIVED_TODAY: 0,
                                            self.POINTS_USED_TODAY: 0,
                                            self.NEGATIVE_POINTS_USED_TODAY: 0})
        self._users.add(user_id)

    def _user_exists(self, user_id: str) -> bool:
        """Return True if user_id is in storage."""
        if self._users is None:
            filter_query = "PartitionKey eq '{partition}'".format(partition=self.TOTAL_PARTITION)
            records = self._table_service.query_entities(self._table_name,
                                                            filter=filter_query,
                                                            select='RowKey')
            self._users = {r['RowKey'] for r in records}
        return user_id in self._users

    def _check_user(self, user_id: str):
        """Check if user exists in storage and create a new entry if not."""
        if not self._user_exists(user_id):
            self._create_user_entry(user_id)

    ### Total/current record
    def _move_user_to_new_day(self, user_id: str):
        """Save the daily record and reset daily counts on Total partion."""
        total_record = self._table_service.get_entity(self._table_name,
                                                        self.TOTAL_PARTITION, 
                                                        user_id)
        del total_record['etag']
        self._save_daily_record(total_record)
        self._reset_daily_counts(total_record)

    def _save_daily_record(self, total_record: dict):
        """Get user's Total record and add as a Daily record."""
        record = dict(total_record)
        record['PartitionKey'] = self._get_record_date(record)
        self._table_service.insert_entity(self._table_name, record)

    def _reset_daily_counts(self, total_record: dict):
        """Reset the daily counts on user's Total record."""
        # Create new dict with same PartitionKey and RowKey,
        # but with zeros for the daily counts.
        record = {'PartitionKey': total_record['PartitionKey'],
                    'RowKey': total_record['RowKey'],
                    self.POINTS_RECEIVED_TODAY: 0,
                    self.POINTS_USED_TODAY: 0,
                    self.NEGATIVE_POINTS_USED_TODAY: 0}
        # Merge with existing Total partition record. 
        self._table_service.merge_entity(self._table_name, record)

    ### POINTS Used
    def get_user_points_used_total(self, user_id: str) -> int:
        """Return total number of points used or 0.
        
        The Total fields in the Total partition are always up to date,
        so there is no need to check if record is from a previous day.
        """
        self._check_user(user_id)
        record = self._table_service.get_entity(self._table_name,
                                                partition_key=self.TOTAL_PARTITION,
                                                row_key=user_id,
                                                select=self.POINTS_USED_TOTAL)
        return record[self.POINTS_USED_TOTAL]

    def get_user_points_used(self, user_id: str) -> int:
        """Return number of points used today or 0."""
        self._check_user(user_id)
        select_query = "PartitionKey,RowKey,Timestamp,{}".format(self.POINTS_USED_TODAY)
        record = self._table_service.get_entity(self._table_name,
                                                partition_key=self.TOTAL_PARTITION,
                                                row_key=user_id,
                                                select=select_query)
        if not self._check_date(record['Timestamp']):
            # This record is from a previous day, so need to update table.
            self._move_user_to_new_day(user_id)
            # Since the Total partition was old, the are no points for today.
            return 0
        else:
            # The record is current, so return value.
            return record[self.POINTS_USED_TODAY]

    def add_user_points_used(self, user_id: str, num: int):
        """Add `num` to user's total and daily used points."""
        self._check_user(user_id)
        select_query = "PartitionKey,RowKey,Timestamp,{},{}".format(self.POINTS_USED_TODAY,
                                                self.POINTS_USED_TOTAL)
        record = self._table_service.get_entity(self._table_name,
                                                partition_key=self.TOTAL_PARTITION,
                                                row_key=user_id,
                                                select=select_query)
        del record['etag']
        if not self._check_date(record['Timestamp']):
            # This record is from a previous day, so need to update table.
            self._move_user_to_new_day(user_id)
            # Since the record was old, there are 0 Daily points.
            record[self.POINTS_USED_TOTAL] = num    
        else:
            # The record is current, so update Daily count.
            record[self.POINTS_USED_TODAY] += num
        # Add num to Total count.
        record[self.POINTS_USED_TOTAL] += num
        # # Add ParitiionKey
        # record['PartitionKey'] = self.TOTAL_PARTITION
        # # Add RowKey
        # record['RowKey'] = user_id
        self._table_service.merge_entity(self._table_name, record)

    def get_user_points_received_total(self, user_id: str) -> int:
        """Return total number of points received or 0."""
        self._check_user(user_id)
        record = self._table_service.get_entity(self._table_name,
                                                partition_key=self.TOTAL_PARTITION,
                                                row_key=user_id,
                                                select=self.POINTS_RECEIVED_TOTAL)
        return record[self.POINTS_RECEIVED_TOTAL]

    ### POINTS RECEIVED
    def get_user_points_received(self, user_id: str) -> int:
        """Return number of points received or 0."""
        self._check_user(user_id)
        select_query = "PartitionKey,RowKey,Timestamp,{}".format(self.POINTS_RECEIVED_TODAY)
        record = self._table_service.get_entity(self._table_name,
                                                partition_key=self.TOTAL_PARTITION,
                                                row_key=user_id,
                                                select=select_query)
        if not self._check_date(record['Timestamp']):
            # This record is from a previous day, so need to update table.
            self._move_user_to_new_day(user_id)
            # Since the Total partition was old, the are no points for today.
            return 0
        else:
            # The record is current, so return value.
            return record[self.POINTS_RECEIVED_TODAY]

    def add_user_points_received(self, user_id: str, num: int):
        """Add `num` to user's total received points."""
        self._check_user(user_id)
        select_query = "PartitionKey,RowKey,Timestamp,{},{}".format(self.POINTS_RECEIVED_TODAY,
                                                self.POINTS_RECEIVED_TOTAL)
        record = self._table_service.get_entity(self._table_name,
                                                partition_key=self.TOTAL_PARTITION,
                                                row_key=user_id,
                                                select=select_query)
        del record['etag']
        if not self._check_date(record['Timestamp']):
            # This record is from a previous day, so need to update table.
            self._move_user_to_new_day(user_id)
            # Since the record was old, there are 0 Daily points.
            record[self.POINTS_RECEIVED_TODAY] = num    
        else:
            # The record is current, so update Daily count.
            record[self.POINTS_RECEIVED_TODAY] += num
        # Add num to Total count.
        record[self.POINTS_RECEIVED_TOTAL] += num
        self._table_service.merge_entity(self._table_name, record)

    def get_users_and_scores_total(self) -> list:
        """Return list of tuples (user_id, points_received_total)."""
        filter_query = "PartitionKey eq '{}'".format(self.TOTAL_PARTITION)
        select_query = "Timestamp,RowKey,{}".format(self.POINTS_RECEIVED_TOTAL)
        records = self._table_service.query_entities(self._table_name,
                                                    filter=filter_query,
                                                    select=select_query)
        return [(r['RowKey'], r[self.POINTS_RECEIVED_TOTAL]) for r in records]

    @staticmethod
    def _get_today() -> datetime.date:
        """Return today's date as a string YYYY-MM-DD."""
        return datetime.datetime.today() + datetime.timedelta(hours=6)

    @staticmethod
    def _get_today_str() -> str:
        """Return today's date as a string YYYY-MM-DD."""
        return AzureTableStorage._get_today().strftime('%Y-%m-%d')

    @staticmethod
    def _get_record_date(record: dict) -> datetime.date:
        """Retrieves the TZ aware date from Azure Table entity."""
        return record['Timestamp'].date().strftime('%Y-%m-%d')

    @staticmethod
    def _check_date(ts: datetime.datetime) -> bool:
        """Return True if date is today.
        
        # TODO: Currently working in UTC and not accunting for TZ.
        """
        return ts.date() == AzureTableStorage._get_today().date()

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