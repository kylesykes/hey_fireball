import os
import time
from collections import namedtuple
import re 

#import redis
from slackclient import SlackClient


# creating redis connection
#r = redis.from_url(os.environ.get("REDIS_URL"))


# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")

# constants
AT_BOT = "<@" + BOT_ID + ">"
EXAMPLE_COMMAND = "do"
MAX_POINTS_PER_DAY = 5
EMOJI = ':fireball:'
POINTS = 'shots'

# instantiate Slack & Twilio clients
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

commands = ['leaderboard', POINTS, '{}left'.format(POINTS)]
commands_with_target = [POINTS, 'all']

################
# FireballMessage class
################
class FireballMessage():

    _USER_ID_PATTERN = '<@\w+>'
    _user_id_re = re.compile(_USER_ID_PATTERN)

    def __init__(self, msg):
        self.requestor_id_only = msg['user']
        self.requestor_id = '<@{}>'.format(self.requestor_id_only)
        self.channel = msg['channel']
        self.text = msg['text']
        self.parts = self.text.split()
        self.bot_is_first = self.parts[0] == AT_BOT
        self.target_id = self._extract_valid_user(self.parts[1])
        self.command = self._extract_command()
        self.count = self._extract_count()
        self.valid = None

    def __str__(self):
        return str(vars(self))

    @staticmethod
    def _extract_valid_user(user_str):
        """Check if string is a valid user id.

        Initially just checking for a valid pattern, but eventually need to check 
        if ID is in Slack user list.
        """
        a = FireballMessage._user_id_re.findall(user_str)
        if len(a) > 0:
            return a[0]
        return None
 
    def _extract_command(self):
        """Find the command in the message."""
        if self.target_id:
            cmds = commands_with_target
            idx = 2
        else:
            cmds = commands
            idx = 1
        # TODO: Check length of parts or error handler here.
        if self.parts[idx].lower() in cmds:
            return self.parts[idx].lower()
        return None

    def _extract_count(self):
        if self.target_id:
            idx = 2
        else:
            idx = 1
        if self.parts[idx] == EMOJI:
            return sum(part==EMOJI for part in self.parts[idx:])
        else:
            try:
                return int(self.parts[idx])
            except ValueError:
                pass
    '''
    # Use the following to catch and handle missing methods/properties as we want
    def __getattr__(self, name):
        def wrapper(*args, **kwargs):
            print "{} is an invalid statement.".format(name)
        return wrapper 
    '''
    

#####################
# Storing and retrieving data
#####################

# Dict for storing user-> {score:int, points_used_today}
data = {}

POINTS_USED = 'POINTS_USED'
POINTS_RECEIVED = 'POINTS_RECEIVED'

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


#####################
# Parsing Message
#####################

def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                # This returns after finding the first message containing
                # the bot name. Other messages in this output list will
                # be ignored. This is how the example was set up. My 
                # guess is that this is prevent spamming the bot: this
                # way the bot can be invoked only once per READ_WEBSOCKET_DELAY.
                return extract_fireball_info(output)
    return None


def is_valid_message(fireball_message):
    """Determines if the message contained in the FireballMessage instance is valid."""
    if (fireball_message.bot_is_first
            and fireball_message.command):
            return True
    return False


def extract_fireball_info(slack_msg):
    """Extract relevant info from slack msg and return a FireballInfo instance.

    If required info is missing or the format is not recognized, set valid=False 
    and return instance.
    """
    fireball = FireballMessage(slack_msg)

    # Make sure bot is first.
    if fireball.bot_is_first:

        # Handle `all` command.
        if fireball.command == 'all':
            fireball.command = 'give'
            fireball.count = get_user_points_remaining(fireball.requestor_id)
    
        # Determine if the `give` command was implied.
        if (fireball.command is None
                and fireball.target_id
                and fireball.count):
            fireball.command = 'give'
    
    fireball.valid = is_valid_message(fireball)
    return fireball   


#####################
# Executing commands
#####################

def handle_command(fireball_message):
    """
        Receive a valid FireballMessage instance and 
        execute the command.
    """
    msg = ''
    attach = None
    if fireball_message.command == 'give':
        # Determine if requestor has enough points to give.
        if check_points(fireball_message.requestor_id, fireball_message.count):
            # Add points to target score.
            add_user_points_received(fireball_message.target_id, fireball_message.count)
            # Add points to requestor points used.
            add_user_points_used(fireball_message.requestor_id, fireball_message.count)
            msg = '{} gave {} {} to {}'.format(fireball_message.requestor_id,
                                                        fireball_message.count,
                                                        POINTS,
                                                        fireball_message.target_id)
        else:
            # Requestor lacks enough points to give.
            msg = '{} does not have enough {}!'.format(fireball_message.requestor_id, POINTS)    

    elif fireball_message.command == POINTS:
        if fireball_message.target_id:
            # Return target's score.
            score = get_user_points_received(fireball_message.target_id)
            msg = '{} has received {} {}'.format(fireball_message.target_id, score, POINTS)
        else:
            # Return requestor's score.
            score = get_user_points_received(fireball_message.requestor_id)
            msg = '{} has received {} {}'.format(fireball_message.requestor_id, score, POINTS)

    elif fireball_message.command == 'leaderboard':
        # Post the leaderboard
        msg = "Leaderboard"
        attach = generate_leaderboard()

    else:
        # Message was not valid, so 
        msg = '{}: I do not understand your message. Try again!'.format(fireball_message.requestor_id)
    
    # Post message to Slack.
    slack_client.api_call("chat.postMessage", channel=fireball_message.channel, 
                    text=msg, as_user=True, attachments=attach)



def give_fireball(user_id, number_of_points):
    """Add `number_of_points` to `user_id`'s total score.
    """
    add_user_points_received(user_id, number_of_points) 


def remove_points(user_id, number_of_points):
    """
    """
    pass 


def check_points(user_id, number_of_points):
    """Check to see if user_id has enough points remaining today.
    """
    return get_user_points_remaining(user_id) >= number_of_points

'''       
colors = ['#36a64f',
'#FF5733',
'#DAF7A6',
'#FFC300',
'#C70039',
'#900C3F'
]
'''
colors= ['#d4af37', '#c0c0c0', '#cd7f32', '#36a64f']

def leaderboard_item(user, score, idx):
    """Generate a leaderboard item."""
    return    {
            "fallback": "{}: {}".format(user, score),
            "color": colors[min(idx, len(colors))],
            "title":  "{}: {}".format(user, score)
        }

def generate_leaderboard():
    """Generate a formatted leaderboard."""
    # Get sorted list of all users and their scores.
    leaders = sorted(get_users_and_scores(), key=lambda tup: tup[1], reverse=True)
    # Create list of leaderboard items.
    board = [leaderboard_item(tup[0], tup[1], idx) for idx, tup in enumerate(leaders)]
    # Add test to the first element.
    board[0]["pretext"] = "HeyFireball Leaderboard"
    return board

if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1  # 1 second delay between reading from firehose
    if slack_client.rtm_connect():
        print("HeyFireball connected and running!")
        while True:
            # Parse messages and look for EMOJI.
            fireball_message = parse_slack_output(slack_client.rtm_read())
            # Check if any messages were found containing EMOJI.
            if fireball_message:
                #print(fireball_message)
                # Check if there was a valid message.
                if fireball_message.valid:
                    handle_command(fireball_message)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
