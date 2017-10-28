# -*- coding: utf-8 -*-
"""
This module encapsulates interations with a storage mechanism
that holds informatoin such as user scores, remaining points
for user, etc.

This module exposes an API via module level functions for
returning user scores, incrementing user scores, etc. 

The abstract class `Storage` defines the methods that this
modules needs in order to interact with a storage 
mechanism. This module contains two subclasses: redis and
inmemory. Additional subclasses can be made that allow 
the use of any appropriate storage mechanism (database,
flat-file, etc.)
"""
import os

try:
    import redis
except ImportError:
    redis = None

_storage = None


#####################
# API
#####################

def set_storage(storage_type: str):
    """Set the storage mechanism."""
    if storage_type == 'inmemory'
        _storage = 


def get_user_points_remaining(user_id):
    """Return the number of points remaining for user."""
    if user_id in data:
        used_pts = data[user_id].get(POINTS_USED, 0)
        return MAX_POINTS_PER_DAY - used_pts
    else:
        return MAX_POINTS_PER_DAY


def add_user_points_used(user_id, num):
    """Add `num` to user's total used points."""
    user_data = data.setdefault(user_id, {})
    user_data[POINTS_USED] = user_data.get(POINTS_USED, 0) + num


def get_user_points_received(user_id):
    """Return the number of points received by this user."""
    if user_id in data:
        return data[user_id].get(POINTS_RECEIVED, 0)
    else:
        return 0


def add_user_points_received(user_id, num):
    """Add `num` to user's total received points."""
    user_data = data.setdefault(user_id, {})
    user_data[POINTS_RECEIVED] = user_data.get(POINTS_RECEIVED, 0) + num


def get_users_and_scores():
    """Return list of (user, score) tuples."""
    return [(k, v[POINTS_RECEIVED]) for k,v in data.items()]


class Storage():
    """Class that defines how module storage functions 
    interact with a storage provider.
    """
    def user_exists(user_id: str):
        """Return True if user_id is in storage."""
        pass

    def get_user_points_used(user_id: str):
        """Return number of points used or 0."""
        pass

    def add_user_points_used(user_id: str, num: int):
        """Add `num` to user's total used points.""" 
        pass

    def get_user_points_received(user_id: str):
        """Return number of points received or 0."""
        pass

    def add_user_points_received(user_id: str, num: int):
        """Add `num` to user's total received points."""
        pass

    def get_users_and_scores():
        """Return list of tuples (user_id, points_received)."""
        pass


class RedisStorage(Storage):
    """Implementation of `Storage` that uses Redis.
    
    Redis server's URL should be in env var `REDIS_URL`.
    """

    POINTS_USED = 'POINTS_USED'
    POINTS_RECEIVED = 'POINTS_RECEIVED'

    def __init__(self):
        super().__init__()
        # Check is Redis library is installed.
        if redis is None:
            raise Exception('Redis package not installed!')
        self._redis = redis.from_url(os.environ.get("REDIS_URL"))
        
    def user_exists(user_id: str):
        """Return True if user_id is in storage."""
        pass

    def get_user_points_used(user_id: str):
        """Return number of points used or 0."""
        pass

    def add_user_points_used(user_id: str, num: int):
        """Add `num` to user's total used points.""" 
        pass

    def get_user_points_received(user_id: str):
        """Return number of points received or 0."""
        pass

    def add_user_points_received(user_id: str, num: int):
        """Add `num` to user's total received points."""
        pass

    def get_users_and_scores():
        """Return list of tuples (user_id, points_received)."""
        pass   


class InMemoryStorage(Storage):
    """Implementation of `Storage` that uses a dict in memory.
    """

    POINTS_USED = 'POINTS_USED'
    POINTS_RECEIVED = 'POINTS_RECEIVED'

    def __init__(self):
        super().__init__()
        # Check is Redis library is installed.
        self._data = dict()
        
    def user_exists(user_id: str):
        """Return True if user_id is in storage."""
        user_id in data:


        used_pts = data[user_id].get(POINTS_USED, 0)

    def get_user_points_used(user_id: str):
        """Return number of points used or 0."""
        pass

    def add_user_points_used(user_id: str, num: int):
        """Add `num` to user's total used points.""" 
        pass

    def get_user_points_received(user_id: str):
        """Return number of points received or 0."""
        pass

    def add_user_points_received(user_id: str, num: int):
        """Add `num` to user's total received points."""
        pass

    def get_users_and_scores():
        """Return list of tuples (user_id, points_received)."""
        pass  

#####################
# Storing and retrieving data
#####################

# Dict for storing user-> {score:int, points_used_today}
data = {}

POINTS_USED = 'POINTS_USED'
POINTS_RECEIVED = 'POINTS_RECEIVED'



