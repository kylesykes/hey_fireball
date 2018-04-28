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
def bot_first_fireball_message(mock_client, mocker, bot_first_message, 
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
       
    return FireballMessage(msg=bot_first_message)


@pytest.fixture(scope='function')
@mock.patch('slackclient.SlackClient.api_call')
def single_user_first_fireball_message(mock_client, mocker, single_user_first_message,
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

    return FireballMessage(msg=single_user_first_message)


class TestBotFirstFireballMessage:
    def test_requestor_id_only(self, bot_first_fireball_message):
        assert bot_first_fireball_message.requestor_id_only == '12345'

    def test_bot_is_first(self, bot_first_fireball_message):
        assert bot_first_fireball_message.bot_is_first == True

    def test_extract_count(self, bot_first_fireball_message):
        assert bot_first_fireball_message._extract_count() == 2

    def test_extract_targets(self, bot_first_fireball_message):
        assert len(bot_first_fireball_message._extract_targets()) == 0


class TestSingleUserFirstFireballMessage:
    def test_requestor_id_only(self, single_user_first_fireball_message):
        assert single_user_first_fireball_message.requestor_id_only == '12345'

    def test_bot_is_first(self, single_user_first_fireball_message):
        assert single_user_first_fireball_message.bot_is_first == False

    def test_extract_count(self, single_user_first_fireball_message):
        assert single_user_first_fireball_message._extract_count() == 2

    def test_extract_targets(self, single_user_first_fireball_message):
        assert len(single_user_first_fireball_message._extract_targets()) == 1

    def test_extract_command(self, single_user_first_fireball_message, 
                             points):
        assert single_user_first_fireball_message._extract_command() == points

    
        



    
