# Standard imports
import os
import time
from collections import namedtuple
import re 
import json

from typing import Dict, List

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
SELF_POINTS = os.environ.get('SELF_POINTS', "DISALLOW")

# constants
AT_BOT = "<@" + BOT_ID + ">"

MAX_POINTS_PER_DAY = 5
#EMOJI = ':fireball:'
#POINTS = 'shots'

# instantiate Slack & Twilio clients
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

commands = ['leaderboard', 'fullboard', POINTS, '{}left'.format(POINTS), 'setpm']
commands_with_target = [POINTS, 'all']

user_list = slack_client.api_call("users.list")['members']
user_name_lookup = {x['id'] : x['name'] for x in user_list}  # U1A1A1A1A : kyle.sykes

def get_username(user_id: str, user_name_lookup: Dict[str, str]) -> str:
    """Get username from ``user_name_lookup`` dictionary

    Parameters
    ----------
    user_id
        Slack user ID
    user_name_lookup
        Dictionary of slack_id : username
    
    Returns
    -------
    str
        Slack username associated with ``user_id``

    """
    try:
        return user_name_lookup[user_id]
    except KeyError:
        return user_id

################
# FireballMessage class
################
class FireballMessage():
    """Class to parse slack messages for Fireball bot

    Attributes
    ----------
    requestor_id_only : str
        User Id of person that sent the message
    requestor_id : str
        Formatted string for Slack to display requestor username properly
    requestor_name : str
        Username display name for requestor
    channel : str
        Channel the message was received in
    text : str
        Text of the message
    parts : list
        ``text`` split on spaces
    bot_is_first : bool
        Boolean flag determining whether the bot name was the first
        thing in the message or not
    valid : bool
        Boolean determining if message is a message intended for
        bot or not (default None)
    target_id : str
        The intended target of points to be given
    target_id_only : str
        User Id of the intended recipient of points
    target_name : str
        Slack username of the target
    command : str
        Command given or intepreted
    count : int
        Count of number of points to be given
    setting : int
        Toggle for whether PMs should be sent to the user or not
    ts
        Storing thread_ts of message
    """

    _USER_ID_PATTERN = '^<@\w+>$'
    _user_id_re = re.compile(_USER_ID_PATTERN)

    def __init__(self, msg: Dict):
        """
        Parameters
        ----------
        msg
            Dictionary of the message from the Slack API
        """
        self.requestor_id_only = msg['user']
        self.requestor_id = f'<@{self.requestor_id_only}>'
        try:
            self.requestor_name = user_name_lookup[self.requestor_id_only]
        except KeyError:
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
                except KeyError:
                    self.target_name = self.target_id
            else:
                self.target_id_only = None
                self.target_name = self.target_id
            self.command = self._extract_command()
            self.count = self._extract_count()
            self.setting = self._extract_setting() # Find on/off or assume toggle
            self.ts = msg['ts'] # Store the thread_ts

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
        idx = sum([bool(self.bot_is_first), bool(self.target_id)])
        if len(self.parts) > idx:
            cmds = commands_with_target if self.target_id else commands
            if self.parts[idx].lower() in cmds:
                 return self.parts[idx].lower()

    def _extract_count(self):
        """Extract the count of EMOJI in the message."""
        idx = sum([bool(self.bot_is_first), bool(self.target_id)])
        if len(self.parts) > idx:
            if self.parts[idx] == EMOJI:
                return sum(part==EMOJI for part in self.parts[idx:])
            else:
                try:
                    return int(self.parts[idx])
                except ValueError:
                    pass

    def _extract_setting(self):
        if self.bot_is_first:
            idx = 2
            curPref = get_pm_preference(self.requestor_id)
            if len(self.parts) < 3:
                #Act as a toggle
                if curPref:
                    return 0
                else:
                    return 1
            if self.parts[idx].lower() == 'on' and not curPref:
                return 1
            elif self.parts[idx].lower() == 'off' and curPref:
                return 0
            else:
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
    elif storage_type == 'azuretable':
        _storage = storage.AzureTableStorage()
    else:
        raise ValueError('Unknown storage type.')


def get_user_points_remaining(user_id: str) -> int:
    """Return the number of points remaining for user today."""
    used_pts = _storage.get_user_points_used(user_id)
    return MAX_POINTS_PER_DAY - used_pts
    
def add_user_points_used(user_id: str, num: int):
    """Add `num` to user's total used points."""
    _storage.add_user_points_used(user_id, num)

def get_user_points_received_total(user_id: str) -> int:
    """Return the number of points received by this user total."""
    return _storage.get_user_points_received_total(user_id)

def add_user_points_received(user_id: str, num: int):
    """Add `num` to user's total and today's received points."""
    _storage.add_user_points_received(user_id, num)

def get_users_and_scores() -> List:
    """Return list of (user, total points received) tuples."""
    return _storage.get_users_and_scores_total()

def get_pm_preference(user_id: str) -> int:
    """Return user's PM Preference"""
    return _storage.get_pm_preference(user_id)

def set_pm_preference(user_id: str, pref: int):
    """Set user's PM Preference"""
    _storage.set_pm_preference(user_id, pref)


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


def is_valid_message(fireball_message: FireballMessage) -> bool:
    """Determines if the message contained in the 
    FireballMessage instance is valid.
    
    Parameters
    ----------
    fireball_message
        Instance of FireballMessage
        
    Returns
    -------
    bool
        True if ``fireball_message`` is valid, False otherwise
        
    """
    if fireball_message.command:
        return True
    return False


def extract_fireball_info(slack_msg: Dict) -> FireballMessage:
    """Extract relevant info from slack msg and return a FireballInfo instance.

    If required info is missing or the format is not recognized, set valid=False 
    and return instance.

    Parameters
    ----------
    slack_msg
        Dictionary of the message from the Slack API
    
    Returns
    -------
    fireball
        FireballMessage instance with (if available) parsed 
        commands

    """
    fireball = FireballMessage(slack_msg)

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

def handle_command(fireball_message: FireballMessage):
    """
        Receive a valid FireballMessage instance and 
        execute the command.

    Parameters
    ----------
    fireball_message
        Instance of ``FireballMessage`` class

    """
    msg = ''
    attach = None
    if fireball_message.command == 'give':
        # Check if self points are allowed.
        if SELF_POINTS == 'DISALLOW' and (fireball_message.requestor_id == fireball_message.target_id):
            msg = 'You cannot give points to yourself!'
            send_message_to = fireball_message.requestor_id_only
        # Determine if requestor has enough points to give.
        elif check_points(fireball_message.requestor_id, fireball_message.count):
            # Add points to target score.
            add_user_points_received(fireball_message.target_id, fireball_message.count)
            # Add points to requestor points used.
            add_user_points_used(fireball_message.requestor_id, fireball_message.count)
            msg = f'You received {fireball_message.count} {POINTS} from {fireball_message.requestor_name}'
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
        points_rmn = get_user_points_remaining(fireball_message.requestor_id)
        msg = f"You have {points_rmn} {POINTS} remaining"
        send_message_to = fireball_message.requestor_id_only

    elif fireball_message.command == 'setpm':
        set_pm_preference(fireball_message.requestor_id, fireball_message.setting)
        if fireball_message.setting:
            msg = "Receive PM's: On"
        else:
            msg = "Receive PM's: Off\n*Warning:* _Future messages that were sent only to you will look like this. This type of response does not typically persist between slack sessions._"
        send_message_to = fireball_message.requestor_id_only
    else:
        # Message was not valid, so
        msg = f'{fireball_message.requestor_id}: I do not understand your message. Try again!'
        send_message_to = fireball_message.channel
    ## Send message
    if (fireball_message.command == 'fullboard' or
            fireball_message.command == 'leaderboard'):
        slack_client.api_call("chat.postMessage", channel=send_message_to,
                              text=msg, as_user=True, attachments=attach,
                              thread_ts=fireball_message.ts)
    else:
        # Post message to Slack.
        if (send_message_to == fireball_message.requestor_id_only and
                get_pm_preference(fireball_message.requestor_id) == 0):
            slack_client.api_call("chat.postEphemeral", channel=fireball_message.channel,
                                  text=msg, user=fireball_message.requestor_id_only,
                                  attachments=attach)
        elif (send_message_to == fireball_message.target_id_only and
              get_pm_preference(fireball_message.target_id) == 0):
            slack_client.api_call("chat.postEphemeral", channel=fireball_message.channel,
                                  text=msg, user=fireball_message.target_id_only,
                                  attachments=attach)
        else:
            slack_client.api_call("chat.postMessage", channel=send_message_to,
                                  text=msg, as_user=True, attachments=attach)


# def give_fireball(user_id, number_of_points):
#     """Add `number_of_points` to `user_id`'s total score.
#     """
#     add_user_points_received(user_id, number_of_points) 


# def remove_points(user_id, number_of_points):
#     """
#     """
#     pass 


def check_points(user_id: str, number_of_points: int):
    """Check to see if user_id has enough points remaining today.

    user_id
        Slack User Id
    number_of_points
        Number of points to be given
    """
    return get_user_points_remaining(user_id) >= number_of_points

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

def leaderboard_item(user: str, score: int, idx: int, colors: List) -> Dict[str, str]:
    """Generate an individual leaderboard item
    
    Parameters
    ----------
    user
        Name of user
    score
        Current score for ``user``
    idx
        Variable for helping track indices
    colors
        List of hex colors for leaderboard colors in 
        descending order

    Returns
    -------
    dict
        Single leaderboard item


    """
    return    {
            "fallback": "{}: {}".format(user, score),
            "color": colors[min(idx, len(colors) - 1)],
            "title":  "{}: {}".format(user, score)
        }

def generate_leaderboard() -> List[Dict[str, str]]:
    """Generate a formatted leaderboard

    Returns
    ----------
    board
        List of leaderboard items

    """
    # Get sorted list of all users and their scores.
    users_and_scores = get_users_and_scores()
    if users_and_scores is not None:
        leaders = sorted(get_users_and_scores(), key=lambda tup: tup[1], reverse=True)
        # Create list of leaderboard items.
        board = [leaderboard_item(get_username(tup[0][2:-1], user_name_lookup), tup[1], idx, colors) for idx, tup in enumerate(leaders[:10])]
        if len(board) > 0:
            # Add test to the first element.
            #board[0]["pretext"] = "Leaderboard"
            pass
        else:
            board = [{"text": f"No users yet. Start giving {POINTS}!!!"}]
        return board
    else:
        return

def generate_full_leaderboard(full: bool = False) -> List[Dict[str, str]]:
    """Generate a formatted leaderboard
    
    Parameters
    ----------
    full
        Flag for returning the full leadboard or a truncated version
        (to not overload a channel)

    Returns
    -------
    list
        list containing a single message formatted to display
        the leaderboard

    """
    # Get sorted list of all users and their scores.
    leaders = sorted(get_users_and_scores(), key=lambda tup: tup[1], reverse=True)
    # Create list of leaderboard items.
    text = '\n'.join([f'{idx + 1}. {get_username(tup[0][2:-1], user_name_lookup)} has {tup[1]} {POINTS}' for idx, tup in enumerate(leaders)])
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
