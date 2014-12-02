"""
Base command class for the TF Server Console.
"""
import os
import sys
import shlex
import json
from cmd import Cmd
from tfcon import SourceRcon
import getpass
import traceback
from appdirs import user_config_dir
from glob import fnmatch

from termcolor import colored, cprint
from colorama import init
init()

CFG_DIR = user_config_dir("tfcon")
#cprint("CFG_DIR = %s" % (CFG_DIR), 'green')

SETTINGS_FILE = os.path.join(user_config_dir("tfcon"), 'settings.json')
COMPLETE_FILE = os.path.join(user_config_dir("tfcon"), 'complete_raw_%s.json')

DEFAULT_PORT = 27015

#def fixinput(fcn):
#    def fixer(arg):
#        print arg
#        return arg

def get_cfgfile(name):
    """get_cfgfile(name)

    Returns the full path to a confi file.
    """
    return os.path.join(user_config_dir("tfcon"), name + '.json')

class TFConsole(Cmd): #pylint: disable=
    prompt = '> '
    intro = colored("Welcome to the Source RCON CLI.\n", 'green') + \
            colored("Type '?' for help!", 'cyan')

    ruler = colored(Cmd.ruler, 'yellow')

    def __init__(self, *args, **kwargs):
        Cmd.__init__(self)
        self._current_server = None
        self._custom_complete = []
        self._favorites = {}
        if not os.path.exists(CFG_DIR):
            os.makedirs(CFG_DIR)
        self.load_settings()

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as settings:
                    loaded = json.load(settings)
                    self._favorites = loaded.get('favorites', {})
            except Exception:
                print "Error reading autocomplete JSON. Regenerating..."
                self.do_update("")

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w') as settings:
                to_save = {}
                to_save['version'] = 1
                to_save['favorites'] = self._favorites
                json.dump(to_save, settings)
        except Exception:
            print "Error reading autocomplete JSON. Regenerating..."
            self.do_update("")

    def load_autocomplete(self):
        if os.path.exists(COMPLETE_FILE % (self._current_server.host)):
            try:
                with open(COMPLETE_FILE % (self._current_server.host), 'r') as cachefile:
                    loaded = json.load(cachefile)
                    self._custom_complete = loaded.get('complete', [])
            except Exception:
                print "Error reading autocomplete JSON. Regenerating..."
                self.do_update("")
        else:
            print "Cache file not found... forcing creation."
            self.do_update("")

    def do_favorite(self, arg):
        parsed = [item.strip('\'"') for item in shlex.shlex(arg)]
        if parsed[0] == "list":
            cprint("== Saved Servers ==", 'yellow')
            for key in sorted(self._favorites.keys()):
                item = self._favorites[key]
                print "%-20s %10s:%s" % (key, item['address'], item['port'])
        elif parsed[0] == "add":
            fav = self._new_favorite()
            if fav is not None:
                self._favorites[fav[0]] = fav[1]
                # Now save the favorites
                self.save_settings()
        elif parsed[0] == "delete":
            result = self._favorites.pop(parsed[1], None)
            if result is None:
                cprint("ERROR: %s was not in your favorites." % (parsed[1]), 'red')
            else:
                cprint("Removed %s from your favorites." % (parsed[1]), 'green')
                self.save_settings()
        else:
            print(colored("Invalid favorite command. Type 'help favorite' for usage.", 'red'))

    def _new_favorite(self):
        fav = {}
        alias = None
        while alias is None:
            alias = raw_input("Alias: ")
            if alias in self._favorites.keys():
                print(colored("There is already a server with alias %s. Do you want to OVERWRITE it?", 'yellow'))
                answer = raw_input("OVERWRITE yes/[n]o/abort: ")
                if not answer:
                    answer = 'n'
                choice = answer[0].lower()
                # If the choice is yes, just carry on.
                if choice == 'a':
                    return None
                else:
                    alias = None

        fav['address'] = raw_input("Hostname: ")
        fav['port'] = raw_input("Port [%s]: " % (DEFAULT_PORT))
        if not fav['port']:
            fav['port'] = DEFAULT_PORT
        try:
            fav['port'] = int(fav['port'])
        except ValueError:
            print(colored("Invalid Port. Defaulting to %s." % (DEFAULT_PORT), 'red'))
            fav['port'] = DEFAULT_PORT
        fav['password'] = getpass.getpass()
        return (alias, fav)

    def complete_favorite(self, text, line, begidx, endidx):
        cmds = ['list', 'add', 'delete']
        parsed = [item for item in shlex.shlex(line)]
        completed = [item for item in cmds if item.startswith(text)]
        if len(parsed) > 1 and parsed[1] == 'delete':
            completed = [item for item in self._favorites.keys() if item.startswith(text)]
        return completed

    def complete_connect(self, text, line, begidx, endidx):
        completed = [item for item in self._favorites.keys() if item.startswith(text)]
        return completed

    def do_update(self, arg):
        if self._current_server is None:
            print "Can't update without being connected to a server..."
            print "Type 'help connect' for help connecting to one."
            return
        raw_cmd = self.rcon('cvarlist')
        raw_list = raw_cmd.split('\n')[2:-3]
        cmds = []
        self._custom_complete = []
        print "Caching autocomplete for %s..." % (self._current_server.host)
        for cmdstr in raw_list:
            cmd = [item.strip() for item in cmdstr.split(":", 3)]
            if ('sv' in cmd[2] or 'rep' in cmd[2]) or cmd[1] == 'cmd':
                cmds.append(cmd)
                self._custom_complete.append(cmd[0])
        with open(COMPLETE_FILE % (self._current_server.host), 'w') as cachefile:
            json.dump({'version': 1, 'complete': self._custom_complete}, cachefile)
        cprint("Done!", 'green')

    def do_search(self, arg):
        matches = []
        for cmdname in self._custom_complete:
            if fnmatch.fnmatch(cmdname, arg):
                matches.append(cmdname)
        cprint("Found %s matches:" % len(matches))
        print "\n".join(matches)

    def help_update(self):
        print "syntax: update",
        print "-- update the local autocomplete cache"

    def do_systemhelp(self, arg):
        return Cmd.do_help(self, arg)

    def help_systemhelp(self):
        print "syntax: systemhelp",
        print "-- allows access to help when connected to a server"
        print "Note: Alias for 'help', except when connected."
        print "      If connected, the 'help' is sent to the server."

    def help_help(self):
        print "syntax: help",
        print "-- displays help for using TFCon"

    def help_disconnect(self):
        print "syntax: disconnect",
        print "-- disconnect from a server"

    def help_d(self):
        print "syntax: d",
        print "-- disconnect from a server"
        print "Note: Alias for 'disconnect'"

    def do_help(self, arg):
        if self._current_server:
            print self.rcon("help " + arg)
        else:
            return Cmd.do_help(self, arg)

    def completedefault(self, text, line, begidx, endidx):
        print "complete called..."
        print "%s, %s, %s, %s" % (text, line, begidx, endidx)

    def completenames(self, text, *ignored):
        items = Cmd.completenames(self, text, *ignored)
            # Try cvar completion
        items.extend([a for a in self._custom_complete if a.startswith(text)])
        return items

    def do_disconnect(self, arg):
        if self._current_server is not None:
            print "Disconnected from %s." % (self._current_server.host)
            self._current_server = None

    def do_connect(self, server, password=None, port=DEFAULT_PORT):
        if server in self._favorites.keys():
            favorite = self._favorites[server]
            server = favorite['address']
            port = favorite['port']
            password = favorite['password']
        if password is None:
            password = getpass.getpass()
        print "Connecting to %s:%s with password %s." % (server, port, '*' * len(password))
        # TODO: Make this read from favorites
        self._current_server = SourceRcon.SourceRcon(server, port, password)
        result = self.rcon('ping')
        if result is not None:
            cprint("== Connected! ==", 'green')
            self.load_autocomplete()
        else:
            cprint("ERROR: Could not connect...", 'red')

    def help_connect(self):
        print "syntax: connect {server} [password]",
        print "-- quick connect to an rcon server"

    def help_c(self):
        print "syntax: c {server} [password]",
        print "-- quick connect to an rcon server"
        print "Note: Alias for 'connect'"

    def help_tutorial(self):
        print "Welcome to the TFConsole, a command line RCON tool.",
        print ""
        print "To connect type:"
        print "> connect tf.fernferret.com"
        print "You will then be prompted for your password, enter it."
        print ""
        print "Now you can just enter commands at the terminal"

    def default(self, arg):
        if self._current_server is None:
            self.stdout.write('*** Use "connect" to connect to a server first!\n')
        else:
            result = self.rcon(arg)
            if result is None:
                print "Something went wrong when issuing your command!"
            else:
                self.stdout.write(result)

    def rcon(self, *args):
        argstring = " ".join(args)
        try:
            return self._current_server.rcon(argstring)
        except SourceRcon.SourceRconError, e:
            print "== Could not connect to %s! ==" % (argstring)
            traceback.print_exc()
            print dir(e)
            self._current_server = None
        except Exception:
            # Most likely lost network, don't force a server disconnect.
            cprint("== UNKNOWN ERROR ==", 'red')
            traceback.print_exc()
        return None

    def do_exit(self, arg):
        sys.exit(1)

    def help_exit(self):
        print "syntax: exit",
        print "-- terminates the application"

    def cmdloop(self, intro=None):
        print(self.intro)
        while True:
            try:
                Cmd.cmdloop(self, intro="")
                self.postloop()
                break
            except KeyboardInterrupt:
                print("")

    def _build_sm_tree(self):
        tree = {}
        tree['cmds'] = []
        tree['config'] = {}
        tree['credits'] = {}
        tree['cvars'] = {}
        tree['exts'] = ['info', 'list', 'load', 'reload', 'unload']
        tree['plugins'] = ['info', 'list', 'load', 'reload', 'load_lock',
                           'load_unlock', 'unload', 'unload_all', 'refresh']
        tree['profiler'] = ['flush', 'report', 'clear']
        tree['version'] = []
        return tree

    def complete_sm(self, text, line, begidx, endidx):
        if self._current_server is None:
            return
        parsed = [item for item in shlex.shlex(line)]
        sm_tree = self._build_sm_tree()
        # root complete
        completed = [item for item in sm_tree.keys() if item.startswith(text)]
        if len(parsed) > 1 and parsed[1] in sm_tree.keys():
            completed = [item for item in sm_tree[parsed[1]] if item.startswith(text)]
        return completed

    # shortcuts
    do_q = do_exit
    do_c = do_connect
    do_d = do_disconnect
    do_f = do_favorite
    complete_f = complete_favorite
    complete_c = complete_connect

