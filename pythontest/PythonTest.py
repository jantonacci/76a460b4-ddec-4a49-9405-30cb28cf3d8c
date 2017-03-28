#!/usr/bin/env python2
"""
:todo: docstring
"""

import argparse
import datetime
import json
import logging
import os
import random
import re
import shlex
import shutil
import string
import subprocess
import sys
import time
from socket import getfqdn

__version__ = '0.0.01'


def parse_arguments(sys_argv=sys.argv):
    """
    Interpret command line arguments per "docs/SQD Script Test v1.1.txt"
    section (1.a), help text, and their suggested defaults.
    :param sys_argv: the command line arguments from the shell
    :ptype sys_argv: list 
    :return: a validated, known options namespace
    :rtype: argparse.ArgumentParser.parse_known_args()[0]
    """
    parser = argparse.ArgumentParser(version=__version__)
    # "docs/SQD Script Test v1.1.txt" section (1.a.i)
    default = os.path.join(os.getenv('HOME', '.'), 'touchfile.txt')
    help = "Specify a file location and name (default: {})".format(default)
    parser.add_argument('-f', '--file',
                        dest='touch',
                        nargs=1,
                        help=help,
                        metavar='FILENAME',
                        action='store',
                        default=default)
    # "docs/SQD Script Test v1.1.txt" section (1.a.ii)
    default = 2
    help = "Specify how often (touch rate) cron will touch the file "
    help += "specified on the input (default: every "
    help += "{} minutes)".format(default)
    parser.add_argument('-r', '--rate',
                        dest='frequency',
                        help=help,
                        metavar='MINUTES',
                        action='store',
                        default=default,
                        type=int)
    # "docs/SQD Script Test v1.1.txt" section (1.a.iii)
    default = os.path.join(os.getenv('HOME', '.'), 'rotate', 'pythontest')
    help = 'Specify a new log roll over file location and prefix, '
    help += '(default: {})'.format(default)
    parser.add_argument('-p', '--prefix',
                        dest='rename',
                        help=help,
                        metavar='FILEPREFIX',
                        action='store',
                        default=default)
    # "docs/SQD Script Test v1.1.txt" section (1.a.iv)
    default = 0
    help = 'Specify how long the script will run (default: '
    help += '{} minutes for forever, must handle user '.format(default)
    help += 'interrupt in the run forever case)'
    parser.add_argument('-l', '--how-long',
                        dest='duration',
                        help=help,
                        metavar='MINUTES',
                        action='store',
                        default=default,
                        type=int)
    # "docs/SQD Script Test v1.1.txt" section (1.c)
    default = '/var/log/syslog'
    parser.add_argument('-c', '--cron-log',
                        dest='logfile',
                        help=argparse.SUPPRESS,
                        action='store',
                        default=default)
    # "docs/SQD Script Test v1.1.txt" section (1.b) specifies "system crontab" (root)
    # this hidden option can be used to override that requirement for testing
    parser.add_argument('--test',
                        help=argparse.SUPPRESS,
                        action='store_true')
    # Hidden bonus, backup crontab to a file for manual restore
    # Uncomment default to enable automagical goodness
    default = None
    # default = os.path.join(os.getenv('HOME', '.'), 'crontab-{}.txt'.format(time.time()))
    help = 'Specify a backup file location for the current crontab, '
    help += '(default: {})'.format(default)
    parser.add_argument('-b', '--backup',
                        help=argparse.SUPPRESS,
                        metavar='FILECRONTAB',
                        action='store',
                        default=default)
    # options replaces args, only known args are needed
    options, args = parser.parse_known_args(sys_argv)
    exit_code, description = validate_args(args=options)
    if exit_code == 0:
        LOGGER.debug('Command line options all parsed')
        return options
    else:
        msg = 'Validating options returned exit code ' + str(exit_code)
        msg += ':\n\t' + str(description)
        LOGGER.error(msg, exc_info=True)
        exit(exit_code)


def validate_args(args=None):
    """
    Check the command line arguments are acceptable:
      --file: write permission on existing directory name required
      --rate: integer value > 0
      --prefix: write permission on existing directory name required
      --how-long: integer value >= 0
      --user: must be root unless --test present
      --test: false unless --test present
      --cron-log: write permission on existing file name required
      --backup: hidden, disabled - but backs up the current crontab
      Also: Per "docs/SQD Script Test v1.1.txt" section (1.b),
        the SYSTEM crontab is to be used, not the USER's
    :param args: command line arguments namespace
    :ptype args: parser.parse_known_args object
    :return: exit code integer and text description for error (if any)
    :rtype: tuple (int, string)
    """
    try:
        username = os.getenv('USER', 'unprivileged user')
        if username is not 'root' and not args.test:
            msg = 'Superuser needed, current user is ' + format(username)
            msg += '\n\tFor unprivileged users, try hidden option --test'
            return 1, msg
        msg = 'invalid path or write permissions needed, argument --file '
        msg += args.touch
        if not os.access(os.path.dirname(args.touch), os.W_OK):
            return 1, msg
        if os.path.isfile(os.path.abspath(args.touch)):
            if not os.access(args.touch, os.W_OK):
                return 1, msg
        if args.frequency <= 0:
            msg = 'positive integer needed, argument --rate ' + args.frequency
            return 1, msg
        if not os.access(os.path.dirname(args.rename), os.W_OK):
            msg = 'invalid path or write permissions needed, argument '
            msg += '--prefix ' + args.rename
            return 1, msg
        if args.duration < 0:
            msg = 'zero or positive integer needed, argument --rate '
            msg += format(args.duration)
            return 1, msg
        if not os.access(args.logfile, os.R_OK):
            msg = 'invalid path or read permissions needed, argument '
            msg += '--cron-log ' + args.logfile
            msg += '\n\tTry hidden argument --cron-log LOG_FILE'
            return 1, msg
        LOGGER.debug('Command line option checks all passed')
        return 0, 'success'
    except Exception as err:
        return 1, err


def setup_logger(level=logging.ERROR):
    """
    Setup console or other logging for debugging, metrics, stats, etc.
    This is not a requirement, but logging is so much more informative than
    print statements, especially for troubleshooting. Don't you agree?
    :return: logger object
    :rtype: logging.
    """
    # Remote logging to syslog, incl. date/time stamp in details...
    # log_fmt = '%(asctime)s:%(levelname)s:%(name)s:pid %(process)d:'
    # Local logging to console, less is more
    log_fmt = '%(levelname)-7s'
    log_fmt += ':%(filename)s:line %(lineno)-4d:'
    log_fmt += '%(module)s:%(funcName)s:'
    log_fmt += '%(message)s'
    logging.basicConfig(format=log_fmt, level=level)
    # Create random ASCII eight character string for uniqueness
    log_uuid = ''.join(random.choice(string.ascii_letters + string.digits)
                       for _ in range(8))
    # Remote logging to syslog, incl. user and hostname
    log_name = 'log {}:{}@{}'.format(log_uuid,
                                     os.getenv('USER', 'user'),
                                     getfqdn())
    logger = logging.getLogger(name=log_name)
    logger.debug('Logging enabled')
    return logger


class Ops(object):
    """
    Interpret operations per "docs/SQD Script Test v1.1.txt"
    sections 1.b through 1.f, as a class:
        1.b. Modify the system (root) crontab to touch a file
        1.c. Process cron events in logs and update touched file
        1.d. Rotate touched file, renaming with prefix
        1.e. Handle exceptions, incl. user interrupt (CTRL+C)
        1.f. Return error codes success, error, user interrupt (CTRL+C)
    """

    def __init__(self, args=None, log=None):
        """
        Initialize the class - try and assign all features placeholder values
        :param args: valid command line options
        :ptype args: argparse.ArgumentParser.parse_known_args object
        :param log: pre-configured logger
        :pytpe log: logging.getLogger object
        """
        self.args = args
        self.log = log
        self._crontab_backup = None
        self._crontab_runtime = None
        self._standard_loop_starttime = time.time()
        self._standard_loop_runtime = None
        self._standard_loop_count = 0
        self.maxtime = self.args.duration * 60  # convert minutes to seconds
        self.recent_events = {}

    def __enter__(self):
        """
        For ... "with Ops() as ops_instance" open/exit
        :return: Me!
        :rtype: Ops class object instance
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        For ... "with Ops() as ops_instance" open/exit
        :return: exit code 
        :rtype: int
        """
        exit(0)

    def new_cronjob(self):
        """
        Aggregate sub-methods to add a new job to crontab
        :return: None 
        """
        self._cron_backup()
        self._cron_addnew()

    def _cron_addnew(self):
        """
        Append the new job, avoiding duplicates, and call
        sub-method to overwrite entire crontab  
        :return: new crontab text
        :rtype: string
        """
        # Format the new cronjob to run at the requested rate and touch the requested file
        crontab_newjob = '*/{} * * * * touch {}'.format(self.args.frequency, self.args.touch)
        self.log.debug('new crontab job: "{}"'.format(crontab_newjob))
        crontab_alljobs = (self._crontab_runtime + '\n' + crontab_newjob).strip()

        # Do not add the new cronjob again, that would be silly
        if crontab_newjob not in self._cron_runtime():
            return self._cron_overwrite(crontab_alljobs)
        else:
            self.log.debug('self._crontab_runtime\n' + self._crontab_runtime)
            self.log.info('crontab job exists')
            return self._crontab_runtime

    def _cron_overwrite(self, newjobs=None):
        """
        Accept the new job and append it to the current one using system commands 
        :param newjobs: crontab job(s) to append separated by newlines
        :ptype newjobs: string
        :return: new crontab text
        :rtype: string
        """
        if newjobs is not None:
            try:
                cmd_echo = shlex.split('echo "{}"'.format(newjobs.strip()))
                proc_echo = subprocess.Popen(cmd_echo, stdout=subprocess.PIPE)
                cmd_crontab_pipe = shlex.split('crontab - ')
                proc_crontab_pipe = subprocess.Popen(cmd_crontab_pipe,
                                                     stdin=proc_echo.stdout,
                                                     stdout=subprocess.PIPE)
                proc_echo.stdout.close()  # Allow proc_echo to receive a SIGPIPE if proc_crontab_pipe exits
                proc_crontab_pipe.wait()
                self.log.debug('self._crontab_runtime\n' + self._cron_runtime())
                self.log.info('crontab job added')
                return self._cron_runtime()
            except subprocess.CalledProcessError as err:
                self.log.error(err, exc_info=True)
                exit(1)
            except Exception as err:
                raise Exception(err)
        else:
            self.log.error('Missing argument newjobs', exc_info=True)
            exit(1)

    def _cron_runtime(self):
        """
        Read, store current crontab using system calls 
        :return: new crontab text
        :rtype: string
        """
        # Capture the current crontab
        cmd_crontab_l = shlex.split('crontab -l')
        proc_crontab_l = subprocess.Popen(cmd_crontab_l,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT)
        returncode = proc_crontab_l.wait()
        stdoutdata = proc_crontab_l.communicate()[0].strip()

        # If no crontab exists, then add comment or empty string
        if stdoutdata.startswith('no crontab for'):
            stdoutdata = ''
        # For other non-success responses, raise an exception
        elif returncode != 0:
            self.log.error(subprocess.CalledProcessError(returncode, cmd_crontab_l, stdoutdata),
                           exc_info=True)
            exit(1)
        self._crontab_runtime = stdoutdata
        stdoutjson = json.dumps(stdoutdata.strip().split('\n'), indent=4)
        self.log.debug('self._crontab_runtime...\n' + stdoutjson)
        self.log.info('crontab jobs read')
        return self._crontab_runtime

    def _cron_backup(self):
        """
        Maintain a backup crontab copy, may be useful...
        :return: original crontab text
        :rtype: string
        """
        # Retain for future use, like cleanup on exit
        self._crontab_backup = self._cron_runtime()
        stdoutjson = json.dumps(self._crontab_backup.strip().split('\n'), indent=4)
        self.log.debug('self._crontab_backup...\n' + stdoutjson)
        self.log.debug('crontab jobs backed up')
        if self.args.backup is not None:
            try:
                with open(self.args.backup, 'wt') as filehandle:
                    filehandle.write(self._crontab_backup)
            except Exception as err:
                self.log.error(err, exc_info=True)
        return self._crontab_backup

    def _pause_loop(self):
        """
        Pause standard_loop (indirectly via _try_one_exec)
        :return: None
        """
        pause_seconds = self.args.frequency * 60
        time.sleep(pause_seconds)

    def standard_loop(self):
        """
        Handle loop variations based on self.args.duration per
         "docs/SQD Script Test v1.1.txt" section (1.a.iv.)
        :return: None
        """
        if self.args.duration == 0:
            # Run forever, unless interrupted by signals
            while True:
                self._try_one_exec()
        else:
            # Run until timeout self.args.duration exceeded
            #  or interrupted by signals
            while not self._exceeded_duration():
                self._try_one_exec()

    def _exceeded_duration(self):
        """
        Handle loop variations based on self.args.duration per
         "docs/SQD Script Test v1.1.txt" section (1.a.iv.) for
          non-zero values in self.args.duration
        :return: None
        """
        self._standard_loop_runtime = time.time() - self._standard_loop_starttime
        self.log.debug('runtime = {}'.format(self._standard_loop_runtime))
        self.log.debug('maxtime = {}'.format(self.maxtime))
        if self._standard_loop_runtime >= self.maxtime:
            self.log.debug('overrun = {}'.format(self._standard_loop_runtime - self.maxtime))
            return True
        return False

    def _try_one_exec(self):
        """
        Aggregate the various tasks in "docs/SQD Script Test v1.1.txt"
        sections (b. to f.) and handle interrupt signals as successful exits
        :return: exit code
        :rtype : int
        """
        try:
            self._standard_loop_count += 1
            self.parse_logfile()
            self.update_touchfile()
            self.rotate_touchfile()
            self._pause_loop()
        except KeyboardInterrupt:
            self.log.warning('Loop terminated by interrupt signal')
            exit(0)

    def update_touchfile(self):
        """
        Per "docs/SQD Script Test v1.1.txt" section (c.) update
        the touch file with parsed logfile information
        :return: None
        """
        if self.recent_events:
            touch_append = self.recent_events.get('start')
            touch_append += ': cron touch command events count '
            touch_append += str(self.recent_events.get('count'))
            other_events = [event for event in self.recent_events.get('events', [])
                            if 'warning' in event.lower() or 'error' in event.lower()]
            # other_events = [event for event in self.recent_events.get('events', [])
            #                 if 'CMD (touch {})'.format(self.args.touch) not in event]
            # other_events = self.recent_events.get('events', [])
            if len(other_events) > 0:
                msg = 'Found {} interesting events '.format(len(other_events))
                msg += "in self.recent_events['events'][0:{}]".format(len(self.recent_events.get('events', [])))
                self.log.debug(msg)
                touch_append += ', {} other events:\n'.format(len(other_events))
                touch_append += json.dumps(other_events, sort_keys=True, indent=4) + '\n'
            if '\n' in touch_append:
                self.log.debug('Appended...\n{}\n...to touch file "{}"'.format(touch_append.strip(),
                                                                               self.args.touch))
            else:
                self.log.debug('Appended "{}" to touch file "{}"'.format(touch_append.strip(),
                                                                         self.args.touch))
            try:
                with open(self.args.touch, 'at') as filehandle:
                    filehandle.write(touch_append.strip() + '\n')
            except Exception as err:
                self.log.error(err, exc_info=True)
                exit(1)
        else:
            self.log.debug('No keys in self.recent_events')

    def parse_logfile(self):
        """
        Per "docs/SQD Script Test v1.1.txt" section (c.) read the 
        the cron logfile and store events within the accepted time
        window (last 7 minutes)
        :return: log file review results from last 7 minutes
        :rtype: dict
        """
        history_minutes = 7
        start = datetime.datetime.utcnow()
        touch_count = 0
        cron_events = []
        re.compile(r' CROND\[[0-9][0-9]*\]: \(.*\) CMD')
        self.recent_events = {}
        try:
            # Assuming entire file fits in memory, otherwise... boom.
            for line in reversed(open(self.args.logfile, 'rt').readlines()):
                if ' CROND[' in line:
                    # Current four digit year, unexpected results on New Years Eve
                    #   What are you doing in the office?
                    event_datetime = start.strftime('%Y ') + line[:16].strip()
                    # Append logfile's abbreviated date and time stamp, ex. "Mar 27 18:10:01"
                    # String conversion to datetime object
                    event_datetime = datetime.datetime.strptime(event_datetime,
                                                                "%Y %b %d %H:%M:%S")
                    # TODO: Consider excluding
                    if start - datetime.timedelta(minutes=history_minutes) < event_datetime:
                        if 'CMD (touch {})'.format(self.args.touch) in line:
                            touch_count += 1
                        cron_events.append(line.strip())
                    else:
                        break
            msg = 'Checked ' + self.args.logfile
            msg += ' at ' + start.isoformat()
            msg += ', found ' + str(touch_count)
            msg += ' cron touch events for file ' + self.args.touch
            self.log.debug(msg)
            self.recent_events = {'start': start.isoformat(),
                                  'count': touch_count,
                                  'events': cron_events}
            return self.recent_events
        except Exception as err:
            self.log.error(err, exc_info=True)
            return self.recent_events

    def rotate_touchfile(self):
        """
        Per "docs/SQD Script Test v1.1.txt" section (d.) rotate
        the touch file, renaming based on self.args.prefix
        :return: None
        """
        rotate_interval = 15
        rotate_filename = self.args.rename + '-' + str(time.time())[:-3] + '.txt'
        remaining_loops = self._standard_loop_count % rotate_interval
        if remaining_loops == 0:
            try:
                shutil.move(self.args.touch, rotate_filename)
            except Exception as err:
                self.log.error(err, exc_info=True)
                exit(1)
        else:
            msg = 'Insufficient loops to rotate touch file, need +/- '
            msg += str(remaining_loops) + ' more to reach '
            msg += str(rotate_interval)
            self.log.debug(msg)


if __name__ == '__main__':
    LOGGER = setup_logger(level=logging.DEBUG)
    ARGS = parse_arguments(sys_argv=sys.argv)
    with Ops(ARGS, LOGGER) as OPS:
        OPS.new_cronjob()
        OPS.standard_loop()
