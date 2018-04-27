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
                         '<@heyfireball> :fireball::fireball:'])
def bot_first_message(request):
    """Sample valid message from Slack for testing
    """
    return {
        'user': '12345',
        'channel': 'test_channel',
        'text': request.param,
        'ts': '1'
    }


@pytest.fixture(scope="module",
                params=['<@12345> :fireball: :fireball:',
                        '<@12345> :fireball::fireball:',
                        '<@12345>:fireball::fireball:',
                        '<@12345><@heyfireball>:fireball::fireball:',
                        ':fireball::fireball: <@12345>',
                        ':fireball:<@12345>:fireball:'])
def single_user_first_message(request):
    """Sample valid message from Slack for testing
    """
    return {
        'user': '12345',
        'channel': 'test_channel',
        'text': request.param,
        'ts': '1'
    }
