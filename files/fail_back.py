#!/usr/bin/python3
import logging
import os.path
import subprocess
from subprocess import call
import sys
import time

from configparser import ConfigParser
from six.moves import input

from bcolors import bcolors


INFO = bcolors.OKGREEN
INPUT = bcolors.OKGREEN
WARN = bcolors.WARNING
FAIL = bcolors.FAIL
END = bcolors.ENDC
PREFIX = "[Failback] "
PLAY_DEF = "../examples/dr_play.yml"
report_name = "report-{}.log"


class FailBack():

    def run(self, conf_file, log_file, log_level):
        log = self._set_log(log_file, log_level)
        log.info("Start failback operation...")
        dr_tag = "fail_back"
        dr_clean_tag = "clean_engine"
        target_host, source_map, var_file, vault, ansible_play = \
            self._init_vars(conf_file)
        report = report_name.format(int(round(time.time() * 1000)))
        log.info("\ntarget_host: %s \n"
                 "source_map: %s \n"
                 "var_file: %s \n"
                 "vault: %s \n"
                 "ansible_play: %s \n"
                 "report log: /tmp/%s \n",
                 target_host,
                 source_map,
                 var_file,
                 vault,
                 ansible_play,
                 report)

        cmd = []
        cmd.append("ansible-playbook")
        cmd.append(ansible_play)
        cmd.append("-t")
        cmd.append(dr_clean_tag)
        cmd.append("-e")
        cmd.append("@" + var_file)
        cmd.append("-e")
        cmd.append("@" + vault)
        cmd.append("-e")
        cmd.append(" dr_source_map=" + target_host)
        cmd.append("--vault-password-file")
        cmd.append("vault_secret.sh")
        cmd.append("-vvv")

        cmd_fb = []
        cmd_fb.append("ansible-playbook")
        cmd_fb.append(ansible_play)
        cmd_fb.append("-t")
        cmd_fb.append(dr_tag)
        cmd_fb.append("-e")
        cmd_fb.append("@" + var_file)
        cmd_fb.append("-e")
        cmd_fb.append("@" + vault)
        cmd_fb.append("-e")
        cmd_fb.append(" dr_target_host=" + target_host
                      + " dr_source_map=" + source_map
                      + " dr_report_file=" + report)
        cmd_fb.append("--vault-password-file")
        cmd_fb.append("vault_secret.sh")
        cmd_fb.append("-vvv")

        # Setting vault password
        vault_pass = input(
            INPUT + PREFIX + "Please enter vault password (In case of "
            "plain text please press ENTER): " + END)
        os.system("export vault_password=\"" + vault_pass + "\"")
        log.info("Starting cleanup process of setup %s"
                 " for oVirt ansible disaster recovery", target_host)
        print("\n%s%sStarting cleanup process of setup '%s'"
              " for oVirt ansible disaster recovery%s"
              % (INFO,
                  PREFIX,
                  target_host,
                  END))
        log.info("Executing cleanup command: %s", ' '.join(map(str, cmd)))
        if log_file is not None and log_file != '':
            self._log_to_file(log_file, cmd)
        else:
            self._log_to_console(cmd, log)

        log.info("Finished cleanup of setup %s"
                 " for oVirt ansible disaster recovery", source_map)
        print("\n%s%sFinished cleanup of setup '%s'"
              " for oVirt ansible disaster recovery%s"
              % (INFO,
                  PREFIX,
                  source_map,
                  END))

        log.info("Start failback DR from setup '%s'", target_host)
        print("\n%s%sStarting fail-back process to setup '%s'"
              " from setup '%s' for oVirt ansible disaster recovery%s"
              % (INFO,
                  PREFIX,
                  target_host,
                  source_map,
                  END))

        log.info("Executing failback command: %s",
                 ' '.join(map(str, cmd_fb)))
        if log_file is not None and log_file != '':
            self._log_to_file(log_file, cmd_fb)
        else:
            self._log_to_console(cmd_fb, log)

        call(["cat", "/tmp/" + report])
        print("\n%s%sFinished failback operation"
              " for oVirt ansible disaster recovery%s"
              % (INFO,
                  PREFIX,
                  END))

    def _log_to_file(self, log_file, cmd):
        with open(log_file, "a") as f:
            proc = subprocess.Popen(cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    universal_newlines=True)
            for line in iter(proc.stdout.readline, ''):
                if 'TASK [' in line:
                    print("\n%s%s%s\n" % (INFO,
                                          line,
                                          END))
                if "[Failback Replication Sync]" in line:
                    print("%s%s%s" % (INFO, line, END))
                f.write(line)
            for line in iter(proc.stderr.readline, ''):
                f.write(line)
                print("%s%s%s" % (WARN,
                                  line,
                                  END))

    def _log_to_console(self, cmd, log):
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
        for line in iter(proc.stdout.readline, ''):
            if "[Failback Replication Sync]" in line:
                print("%s%s%s" % (INFO, line, END))
            else:
                log.debug(line)
        for line in iter(proc.stderr.readline, ''):
            log.warn(line)
        self._handle_result(subprocess, cmd)

    def _handle_result(self, subprocess, cmd):
        try:
            proc = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            # do something with output
        except subprocess.CalledProcessError as e:
            print("%sException: %s\n\n"
                  "failback operation failed, please check log file for "
                  "further details.%s"
                  % (FAIL,
                     e,
                     END))
            exit()

    def _init_vars(self, conf_file):
        """ Declare constants """
        _SECTION = "failover_failback"
        _TARGET = "dr_target_host"
        _SOURCE = "dr_source_map"
        _VAULT = "vault"
        _VAR_FILE = "var_file"
        _ANSIBLE_PLAY = 'ansible_play'
        setups = ['primary', 'secondary']

        """ Declare varialbles """
        target_host, source_map, vault, var_file, ansible_play = \
            '', '', '', '', ''
        settings = ConfigParser()
        settings.read(conf_file)
        if _SECTION not in settings.sections():
            settings.add_section(_SECTION)
        if not settings.has_option(_SECTION, _TARGET):
            settings.set(_SECTION, _TARGET, '')
        if not settings.has_option(_SECTION, _SOURCE):
            settings.set(_SECTION, _SOURCE, '')
        if not settings.has_option(_SECTION, _VAULT):
            settings.set(_SECTION, _VAULT, '')
        if not settings.has_option(_SECTION, _VAR_FILE):
            settings.set(_SECTION, _VAR_FILE, '')
        if not settings.has_option(_SECTION, _ANSIBLE_PLAY):
            settings.set(_SECTION, _ANSIBLE_PLAY, '')
        # We fetch the source map as target host since in failback
        # we do the reverse operation.
        target_host = settings.get(_SECTION, _SOURCE,
                                   vars=DefaultOption(settings,
                                                      _SECTION,
                                                      source_map=None))
        # We fetch the target host as target the source mapping for failback
        # since we do the reverse operation.
        source_map = settings.get(_SECTION, _TARGET,
                                  vars=DefaultOption(settings,
                                                     _SECTION,
                                                     target_host=None))
        vault = settings.get(_SECTION, _VAULT,
                             vars=DefaultOption(settings,
                                                _SECTION,
                                                vault=None))
        var_file = settings.get(_SECTION, _VAR_FILE,
                                vars=DefaultOption(settings,
                                                   _SECTION,
                                                   var_file=None))
        ansible_play = settings.get(_SECTION, _ANSIBLE_PLAY,
                                    vars=DefaultOption(settings,
                                                       _SECTION,
                                                       ansible_play=None))
        while target_host not in setups:
            target_host = input(
                INPUT + PREFIX + "The target setup was not defined. "
                "Please provide the setup which it is failback to "
                "(primary or secondary): " + END)
        while source_map not in setups:
            source_map = input(
                INPUT + PREFIX + "The source mapping was not defined. "
                "Please provide the source mapping "
                "(primary or secondary): " + END)
        while not os.path.isfile(var_file):
            var_file = input("%s%svar file mapping '%s' does not exist. "
                             "Please provide a valid mapping var file: %s"
                             % (INPUT, PREFIX, var_file, END))
        while not os.path.isfile(vault):
            vault = input("%s%spassword file '%s' does not exist."
                          " Please provide a valid password file:%s "
                          % (INPUT, PREFIX, vault, END))
        while (not ansible_play) or (not os.path.isfile(ansible_play)):
            ansible_play = input("%s%sansible play '%s' "
                                 "is not initialized. "
                                 "Please provide the ansible play file "
                                 "to generate the mapping var file "
                                 "with ('%s'):%s "
                                 % (INPUT, PREFIX, str(ansible_play),
                                    PLAY_DEF, END) or PLAY_DEF)
        return target_host, source_map, var_file, vault, ansible_play

    def _set_log(self, log_file, log_level):
        logger = logging.getLogger(PREFIX)
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(message)s')
        if log_file is not None and log_file != '':
            hdlr = logging.FileHandler(log_file)
            hdlr.setFormatter(formatter)
            logger.addHandler(hdlr)
        else:
            ch = logging.StreamHandler(sys.stdout)
            logger.addHandler(ch)
        logger.setLevel(log_level)
        return logger


class DefaultOption(dict):

    def __init__(self, config, section, **kv):
        self._config = config
        self._section = section
        dict.__init__(self, **kv)

    def items(self):
        _items = []
        for option in self:
            if not self._config.has_option(self._section, option):
                _items.append((option, self[option]))
            else:
                value_in_config = self._config.get(self._section, option)
                _items.append((option, value_in_config))
        return _items


if __name__ == "__main__":
    level = logging.getLevelName("DEBUG")
    conf = 'dr.conf'
    log = '/tmp/ovirt-dr.log'
    FailBack().run(conf, log, level)
