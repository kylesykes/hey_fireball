import pytest

@pytest.fixture(scope='module')
def bot_id():
    return 'heyfireball'

@pytest.fixture(scope='module')
def emoji():
    return ':fireball:'

@pytest.fixture(scope='module')
def points():
    return 'shots'


@pytest.fixture(scope="module",
                params=['<@heyfireball> :fireball: :fireball:', 
                         '<@heyfireball> :fireball: :fireball:'])
def valid_message(request):
    """Sample valid message from Slack for testing
    """
    return {
        'user': '12345',
        'channel': 'test_channel',
        'text': request.param,
        'ts': '1'
    }

@pytest.fixture(scope='module')
def invalid_message_1():
    """Sample invalid message from Slack for testing
    """
    return {
        'user': '12345',
        'channel': 'test_channel',
        'text': '<@12345> :fireball: :fireball:',
        'ts': '1'
    }