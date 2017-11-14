# Standard imports
import os
import time
from collections import namedtuple
import re 
import json

# 3rd party imports
from slackclient import SlackClient

# Same package imports
import storage

# Storage info
_storage = None
STORAGE_TYPE = os.environ.get("STORAGE_TYPE", "inmemory")

# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")
EMOJI = os.environ.get('EMOJI')
POINTS = os.environ.get('POINTS')
SELF_POINTS = os.environ.get('SELF_POINTS', "ALLOW")
NEG_POINTS = os.environ.get('NEG_POINTS', "ALLOW")

if NEG_POINTS == "ALLOW":
    NEGATIVE_EMOJI = os.environ.get('NEGATIVE_EMOJI')
    NEGATIVE_POINTS = os.environ.get('NEGATIVE_POINTS')
# constants
AT_BOT = "<@" + BOT_ID + ">"

MAX_POINTS_PER_DAY = 5
MAX_NEG_POINTS_PER_DAY = 3
#EMOJI = ':fireball:'
#POINTS = 'shots'

# instantiate Slack & Twilio clients
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

commands = ['leaderboard', 'fullboard', POINTS, '{}left'.format(POINTS),
            NEGATIVE_POINTS, '-{}left'.format(NEGATIVE_POINTS)]
commands_with_target = [POINTS, 'all', NEGATIVE_POINTS, 'allneg']

user_list = slack_client.api_call("users.list")['members']
user_name_lookup = {x['id'] : x['name'] for x in user_list}  # U1A1A1A1A : kyle.sykes

def get_username(user_id):
    """Return the user's username based on the user_id
       else, return the user_id"""
    try:
        return user_name_lookup[user_id]
    except KeyError:
        return user_id

################
# FireballMessage class
################
class FireballMessage():

    _USER_ID_PATTERN = '^<@\w+>$'
    _user_id_re = re.compile(_USER_ID_PATTERN)

    def __init__(self, msg):
        self.requestor_id_only = msg['user']
        self.requestor_id = f'<@{self.requestor_id_only}>'
        try:
            self.requestor_name = user_name_lookup[self.requestor_id_only]
        except:
            self.requestor_name = self.requestor_id
        self.channel = msg['channel']
        self.text = msg['text']
        self.parts = self.text.split()
        self.bot_is_first = self.parts[0] == AT_BOT
        self.valid = None
        # Check if botname was the only token.
        if len(self.parts) > 1:
            # Extract target.
            if self.bot_is_first: 
                token = self.parts[1]
            else:
                token = self.parts[0] 
            self.target_id = self._extract_valid_user(token)
            if self.target_id is not None:
                self.target_id_only = self.target_id[2:-1]
            # Try to get target username.
            try:
                self.target_name = user_name_lookup[self.target_id_only]
            except:
                self.target_name = self.target_id
            self.command = self._extract_command()
            self.type = self._extract_type()
            self.count = self._extract_count()

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
            if a[0][2:-1] in user_name_lookup.keys():
                return a[0]
        return None
 
    def _extract_command(self):
        """Find the command in the message."""
        #TODO: Clean up this gnarly logic.  Stop hardcoding indices
        if self.bot_is_first:
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
        else:
            if self.target_id:
                cmds = commands_with_target
                idx = 1
            else:
                cmds = commands
                idx = 0
            # TODO: Check length of parts or error handler here.
            if self.parts[idx].lower() in cmds:
                return self.parts[idx].lower()
            return None

    def _extract_type(self):
        if self.bot_is_first:
            if self.target_id:
                idx = 2
            else:
                idx = 1
            if self.parts[idx] == EMOJI:
                return EMOJI
            elif self.parts[idx] == NEGATIVE_EMOJI:
                return NEGATIVE_EMOJI
            else:
                try:
                    return str(self.parts[idx])
                except ValueError:
                    pass

    def _extract_count(self):
        #TODO: Clean up this gnarly logic.  Stop hardcoding indices
        if self.bot_is_first:
            if self.target_id:
                idx = 2
            else:
                idx = 1
            if self.parts[idx] == EMOJI:
                return sum(part == EMOJI for part in self.parts[idx:])
            elif NEG_POINTS == 'ALLOW' and self.parts[idx] == NEGATIVE_EMOJI:
                return sum(part == NEGATIVE_EMOJI for part in self.parts[idx:])
            else:
                try:
                    return int(self.parts[idx]) # May need changes for NEGATIVE_EMOJI?
                except ValueError:
                    pass
        else:
            if self.target_id:
                idx = 1
            else:
                idx = 0
            if self.parts[idx] == EMOJI:
                return sum(part == EMOJI for part in self.parts[idx:])
            elif NEG_POINTS == 'ALLOW' and self.parts[idx] == NEGATIVE_EMOJI:
                return sum(part == NEGATIVE_EMOJI for part in self.parts[idx:])
            else:
                try:
                    return int(self.parts[idx]) # May need changes for NEGATIVE_EMOJI?
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


def set_storage(storage_type: str):
    """Set the storage mechanism.

    Must be set before calling storge functions.
    """
    global _storage
    storage_type = storage_type.lower()
    if storage_type == 'inmemory':
        _storage = storage.InMemoryStorage()
    elif storage_type == 'redis':
        _storage = storage.RedisStorage()
    elif storage_type == 'azuretable':
        _storage = storage.AzureTableStorage()
    else:
        raise ValueError('Unknown storage type.')

# Points used
def get_user_points_remaining(user_id: str, kind: str) -> int:
    """Return the number of points remaining for user today."""
    if kind == EMOJI:
        used_pts = _storage.get_user_points_used(user_id)
        return MAX_POINTS_PER_DAY - used_pts
    if kind == NEGATIVE_EMOJI:
        used_pts = _storage.get_user_neg_points_used(user_id)
        return MAX_NEG_POINTS_PER_DAY - used_pts

def get_user_neg_points_remaining(user_id: str) -> int:
    """Return the number of negative points remaining for user today"""
    used_pts = _storage.get_user_neg_points_used(user_id)
    return MAX_NEG_POINTS_PER_DAY - used_pts

def add_user_neg_points_used(user_id: str, num: int):
    """Add `num` to user's total used negative points."""
    _storage.add_user_neg_points_used(user_id, num)

def add_user_points_used(user_id: str, num: int):
    """Add `num` to user's total used points."""
    _storage.add_user_points_used(user_id, num)

# Points received
def get_user_points_received_total(user_id: str) -> int:
    """Return the number of points received by this user total."""
    return _storage.get_user_points_received_total(user_id)


def add_user_points_received(user_id: str, num: int):
    """Add `num` to user's total and today's received points."""
    _storage.add_user_points_received(user_id, num)

def get_user_neg_points_received(user_id: str):
    """Return the number of negative points received by this user."""
    return _storage.get_user_neg_points_received(user_id)

def add_user_neg_points_received(user_id: str, num: int):
    """Add `num` to user's negative points received"""
    _storage.add_user_neg_points_received(user_id, num)

def get_users_and_scores() -> list:
    """Return list of (user, total points received) tuples."""
    return _storage.get_users_and_scores_total()


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
            if ((output and 'text' in output) and 
                ((AT_BOT in output['text']) or
                (EMOJI in output['text']))):
                # This returns after finding the first message containing
                # the bot name. Other messages in this output list will
                # be ignored. This is how the example was set up. My 
                # guess is that this is prevent spamming the bot: this
                # way the bot can be invoked only once per READ_WEBSOCKET_DELAY.
                return extract_fireball_info(output)
    return None


def is_valid_message(fireball_message):
    """Determines if the message contained in the FireballMessage instance is valid."""
    if fireball_message.command:
        return True
    return False


def extract_fireball_info(slack_msg):
    """Extract relevant info from slack msg and return a FireballInfo instance.

    If required info is missing or the format is not recognized, set valid=False 
    and return instance.
    """
    fireball = FireballMessage(slack_msg)

    # Handle `all` command.
    if fireball.command == 'all':
        fireball.command = 'give'
        fireball.count = get_user_points_remaining(fireball.requestor_id, EMOJI)

    if fireball.command == 'allneg':
        fireball.command = 'giveneg'
        fireball.count = get_user_points_remaining(fireball.requestor_id, NEGATIVE_EMOJI)

    # Determine if the `give` command was implied.
    if (fireball.command is None
            and fireball.target_id
            and fireball.count):
        if fireball.type == EMOJI:
            fireball.command = 'give'
        elif fireball.type == NEGATIVE_EMOJI:
            fireball.command = 'giveneg'

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
    if fireball_message.command == 'give' or fireball_message.command == 'giveneg':
        # Check if self points are allowed.
        if SELF_POINTS == 'DISALLOW' and (fireball_message.requestor_id == fireball_message.target_id):
            msg = 'You cannot give points to yourself!'
            send_message_to = fireball_message.requestor_id_only

        # Determine if requestor has enough points to give.
        elif check_points(fireball_message.requestor_id, fireball_message.count, fireball_message.type):
            if fireball_message.type == EMOJI:
                # Add points to target score.
                add_user_points_received(fireball_message.target_id, fireball_message.count)
                # Add points to requestor points used.
                add_user_points_used(fireball_message.requestor_id, fireball_message.count)
                msg = f'You received {fireball_message.count} {POINTS} from {fireball_message.requestor_name}!'
                send_message_to = fireball_message.target_id_only
            elif fireball_message.type == NEGATIVE_EMOJI:
                # Add points to targets negative score.
                add_user_neg_points_received(fireball_message.target_id, fireball_message.count)
                # Add points to requestor negative points used.
                add_user_neg_points_used(fireball_message.requestor_id, fireball_message.count)
                msg = f'You received {fireball_message.count} negative {POINTS} from {fireball_message.requestor_name}!'
                send_message_to = fireball_message.target_id_only
        else:
            # Requestor lacks enough points to give.
            msg = f'You do not have enough {POINTS}!'
            send_message_to = fireball_message.requestor_id_only

    elif fireball_message.command == POINTS:
        if fireball_message.target_id:
            # Return target's score.
            score = get_user_points_received_total(fireball_message.target_id)
            msg = f'{fireball_message.target_name} has received {score} {POINTS}'
            send_message_to = fireball_message.channel
        else:
            # Return requestor's score.
            score = get_user_points_received_total(fireball_message.requestor_id)
            msg = f'{fireball_message.requestor_name} has received {score} {POINTS}'
            send_message_to = fireball_message.channel

    elif fireball_message.command == 'leaderboard':
        # Post the leaderboard
        msg = "Leaderboard"
        attach = generate_leaderboard()
        send_message_to = fireball_message.channel

    elif fireball_message.command == 'fullboard':
        # Post the leaderboard
        msg = 'Leaderboard'
        #attach = "Full HeyFireball Leaderboard\n" + generate_full_leaderboard()
        attach = generate_full_leaderboard()
        send_message_to = fireball_message.channel

    elif fireball_message.command == f'{POINTS}left':
        # Return requestor's points remaining.
        points_rmn = get_user_points_remaining(fireball_message.requestor_id, EMOJI)
        msg = f"You have {points_rmn} {POINTS} remaining"
        send_message_to = fireball_message.requestor_id_only

    else:
        # Message was not valid, so 
        msg = f'{fireball_message.requestor_id}: I do not understand your message. Try again!'
        send_message_to = fireball_message.channel
    
    # Post message to Slack.
    slack_client.api_call("chat.postMessage", channel=send_message_to, 
                          text=msg, as_user=True, attachments=attach)


def give_fireball(user_id, number_of_points):
    """Add `number_of_points` to `user_id`'s total score.
    """
    add_user_points_received(user_id, number_of_points) 


def remove_points(user_id, number_of_points):
    """
    """
    pass 


def check_points(user_id, number_of_points, kind):
    """Check to see if user_id has enough points remaining today.
    """
    return get_user_points_remaining(user_id, kind) >= number_of_points

'''
fireball color palette
http://www.color-hex.com/color-palette/27418
#f05500	(240,85,0)
#ee2400	(238,36,0)
#f4ac00	(244,172,0)
#ffdb00	(255,219,0)
#ff9a00
'''
colors = ['#d4af37', '#c0c0c0', '#cd7f32', '#36a64f']

def leaderboard_item(user, score, idx):
    """Generate a leaderboard item."""
    return    {
            "fallback": "{}: {}".format(user, score),
            "color": colors[min(idx, len(colors) - 1)],
            "title":  "{}: {}".format(user, score)
        }

def generate_leaderboard():
    """Generate a formatted leaderboard."""
    # Get sorted list of all users and their scores.
    users_and_scores = get_users_and_scores()
    if users_and_scores is not None:
        leaders = sorted(get_users_and_scores(), key=lambda tup: tup[1], reverse=True)
        # Create list of leaderboard items.
        board = [leaderboard_item(get_username(tup[0][2:-1]), tup[1], idx) for idx, tup in enumerate(leaders[:10])]
        if len(board) > 0:
            # Add test to the first element.
            #board[0]["pretext"] = "Leaderboard"
            pass
        else:
            board = [{"text": f"No users yet. Start giving {POINTS}!!!"}]
        return board
    else:
        return

def generate_full_leaderboard(full=False):
    """Generate a formatted leaderboard."""
    # Get sorted list of all users and their scores.
    leaders = sorted(get_users_and_scores(), key=lambda tup: tup[1], reverse=True)
    # Create list of leaderboard items.
    text = '\n'.join([f'{idx + 1}. {get_username(tup[0][2:-1])} has {tup[1]} {POINTS}' for idx, tup in enumerate(leaders)])
    if len(text) == 0:
        text = f"No users yet. Start giving {POINTS}!!!"
    board = {'text':text, 'color':'#f05500'}

    #ee2400
    # Add test to the first element.
    #board[0]["pretext"] = "HeyFireball Leaderboard"
    return [board]

if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1  # 1 second delay between reading from firehose
    set_storage(STORAGE_TYPE)
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
