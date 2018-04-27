import pytest
import os
import mock


@pytest.fixture(scope='module')
def mock_users_list():
    return {
        'id': '12345',
        'name': 'test_user'
    }

@pytest.fixture(scope='module')
def user_name_lookup():
    """Test user name lookup
    """
    return {
        '12345': 'test_user'
    }

@pytest.fixture(scope='function')
@mock.patch('slackclient.SlackClient.api_call')
def fireball_message(mock_client, mocker, valid_message, 
                     bot_id, emoji, points):
    """A test FireballMessage class instance
    """
    # Mock environmental variables
    mocker.patch.dict('os.environ', {'BOT_ID': bot_id,
                                     'EMOJI': emoji,
                                     'POINTS': points})
    mock_setting = mocker.patch('hey_fireball.FireballMessage._extract_setting')
    mock_setting.return_value = 1

    from hey_fireball import FireballMessage
    mock_client.api_call.return_value = {
        'members': {
            'id': '12345',
            'name': 'test_user'
        }
    }

    mock_setting.return_value = 1
       
    return FireballMessage(msg=valid_message)


class TestValidFireballMessage:
    def test_requestor_id_only(self, fireball_message):
        assert fireball_message.requestor_id_only == '12345'

    def test_bot_is_first(self, fireball_message):
        assert fireball_message.bot_is_first == True

    def test_extract_count(self, fireball_message):
        assert fireball_message._extract_count() == 2
        



    
