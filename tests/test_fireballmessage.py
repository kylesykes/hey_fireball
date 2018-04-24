import pytest
import os
import mock

from slackclient import SlackClient

# Setup environmental variables for testing
os.environ['BOT_ID'] = 'heyfireball'
os.environ['EMOJI'] = ':fireball:'
os.environ['POINTS'] = 'shots'



def mock_users_list():
    return {
        'id': '12345',
        'name': 'test_user'
    }

@pytest.fixture(scope='module')
def user_name_lookup():
    return {
        '12345': 'test_user'
    }

@pytest.fixture(scope='module')
def message():
    return {
        'user': '12345',
        'channel': 'test_channel',
        'text': 'Hey <@12345>, did you see my file?'
    }


@mock.patch(SlackClient.api_call)
class TestFireballMessage:
    def __init__(self):
        from hey_fireball import FireballMessage
        pass



    
