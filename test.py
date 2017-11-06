
import os
import datetime
import random
import time

import pytest
import azure.storage.table

import storage


### Fixtures
@pytest.fixture()
def user_id():
    return 'Matt'

@pytest.fixture()
def points_to_add():
    return 3

@pytest.fixture()
def points_received_to_add():
    return 5

@pytest.fixture(scope='module')
def ats():
    TABLE_NAME = os.getenv('TABLE_NAME') + str(random.randint(0, 100000))
    print('\n' + TABLE_NAME)
    ats = storage.AzureTableStorage()
    ats._table_name = TABLE_NAME
    print('\nCreating Azure Table {}...'.format(TABLE_NAME))
    ats._table_service.create_table(TABLE_NAME)
    time.sleep(3)
    yield ats
    print('\nDeleting Azure Table {}...'.format(TABLE_NAME))
    ats._table_service.delete_table(TABLE_NAME)


### Tests
def test_get_user_points_used(ats, user_id):
    assert ats.get_user_points_used(user_id) == 0

def test_add_user_points_used(ats, user_id, points_to_add):
    ats.add_user_points_used(user_id, points_to_add)
    assert ats.get_user_points_used(user_id) == points_to_add
    assert ats.get_user_points_used_total(user_id) == points_to_add
    
def test_get_user_points_received(ats, user_id):
    assert ats.get_user_points_received(user_id) == 0

def test_add_user_points_received(ats, user_id, points_received_to_add):
    ats.add_user_points_received(user_id, points_received_to_add)
    assert ats.get_user_points_received(user_id) == points_received_to_add
    assert ats.get_user_points_received_total(user_id) == points_received_to_add

# Move user to new day and check that the daily is 0 and the total is old value.
# Moving user to new day must happen after all the daily checks are done (above).
def test_move_user_to_new_day(ats, user_id):
    old_record = ats._table_service.get_entity(ats._table_name,
                                              ats.TOTAL_PARTITION,
                                              user_id)
    ats._move_user_to_new_day(user_id)
    new_record = ats._table_service.get_entity(ats._table_name,
                                            ats._get_today_str(),
                                            user_id)
    assert new_record is not None
    fields = [ats.POINTS_USED_TOTAL,
              ats.POINTS_USED_TODAY,
              ats.POINTS_RECEIVED_TOTAL,
              ats.POINTS_RECEIVED_TODAY,
              ats.NEGATIVE_POINTS_USED_TOTAL,
              ats.NEGATIVE_POINTS_USED_TODAY]
    for field in fields:
        assert old_record[field] == new_record[field]

def test_user_points_used_new_day(ats, user_id, points_to_add):
    assert ats.get_user_points_used(user_id) == 0
    assert ats.get_user_points_used_total(user_id) == points_to_add

def test_user_points_received_new_day(ats, user_id, points_received_to_add):
    assert ats.get_user_points_received(user_id) == 0
    assert ats.get_user_points_received_total(user_id) == points_received_to_add