
import os
import datetime
import random
import time

import pytest
import azure.storage.table

import storage


### Fixtures
@pytest.fixture(scope='module')
def user_id():
    return 'Matt'

@pytest.fixture(scope='module')
def points_to_add():
    return 3

@pytest.fixture(scope='module')
def points_received_to_add():
    return 5


@pytest.fixture(scope='module')
def local_storage(user_id):
    local_storage = storage.InMemoryStorage()
    local_storage._create_user_entry(user_id=user_id)
    return local_storage

class TestInMemoryStorage():

    ## Tests
    def test_get_user_points_used(self, local_storage, user_id):
        assert local_storage.get_user_points_used(user_id) == 0

    def test_add_user_points_used(self, local_storage, user_id, points_to_add):
        local_storage.add_user_points_used(user_id, points_to_add)
        assert local_storage.get_user_points_used(user_id) == points_to_add
        assert local_storage.get_user_points_used_total(user_id) == points_to_add
        
    def test_get_user_points_received(self, local_storage, user_id):
        assert local_storage.get_user_points_received(user_id) == 0

    def test_add_user_points_received(self, local_storage, user_id, points_received_to_add):
        local_storage.add_user_points_received(user_id, points_received_to_add)
        assert local_storage.get_user_points_received(user_id) == points_received_to_add
        assert local_storage.get_user_points_received_total(user_id) == points_received_to_add

# Move user to new day and check that the daily is 0 and the total is old value.
# Moving user to new day must happen after all the daily checks are done (above).
# TODO: Implement _move_user_to_new_day method for InMemoryStorage
    # def test_move_user_to_new_day(self, local_storage, user_id):
    #     old_record = local_storage._data[user_id]
    #     self._move_user_to_new_day(user_id)
        
    #     new_record = local_storage._data[user_id]

    #     assert new_record is not None
    #     fields = [local_storage.POINTS_USED_TOTAL,
    #             local_storage.POINTS_USED_TODAY,
    #             local_storage.POINTS_RECEIVED_TOTAL,
    #             local_storage.POINTS_RECEIVED_TODAY,
    #             local_storage.NEGATIVE_POINTS_USED_TOTAL,
    #             local_storage.NEGATIVE_POINTS_USED_TODAY]
    #     for field in fields:
    #         assert old_record[field] == new_record[field]

    # def test_user_points_used_new_day(self, local_storage, user_id, points_to_add):
    #     assert local_storage.get_user_points_used(user_id) == 0
    #     assert local_storage.get_user_points_used_total(user_id) == points_to_add

    # def test_user_points_received_new_day(self, local_storage, user_id, points_received_to_add):
    #     assert local_storage.get_user_points_received(user_id) == 0
    #     assert local_storage.get_user_points_received_total(user_id) == points_received_to_add