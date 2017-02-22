import logging
import re

from kalliope.core.NeuronModule import NeuronModule, InvalidParameterException

logging.basicConfig()
logger = logging.getLogger("kalliope")

class Todotxt (NeuronModule):
    def __init__(self, **kwargs):
        logger.debug("ALLO")
        super(Todotxt, self).__init__(**kwargs)

        self.configuration = {
            'todotxt_file': kwargs.get('todotxt_file', None),
            'priority': kwargs.get('priority', None),
            'project': kwargs.get('project', None),
            'context': kwargs.get('context', None),
            'complete': kwargs.get('complete', False)
        }

        if self._is_parameters_ok():
            tasks = self._get_tasks(self._parse_todotxt(self.configuration['todotxt_file']),
                                         priority = self.configuration['priority'],
                                         project = self.configuration['project'],
                                         context = self.configuration['context'],
                                         complete = self.configuration['complete'])

            logger.debug("Tasks: %s" % tasks)
            # self.say(message)

            task_list = []
            for t in tasks:
                task_list.append({
                    'text': t.task,
                    'priority': t.priority,
                    'complete': t.complete,
                    'contexts': t.context,
                    'projects': t.project,
                })

        self.say({'task_list': task_list, 'count': len(task_list)})

    def _is_parameters_ok(self):
        """
        Check if received parameters are ok to perform operations in the neuron.
        :return: True if parameters are ok, raise an exception otherwise.
        .. raises:: MissingParameterException
        """
        if self.configuration['todotxt_file'] is None:
            raise MissingParameterException("Todotxt need the todo file")

        return True


    def _parse_todotxt(self, todofile):
        with open(todofile, 'r') as file:
            rawfile = file.read()

        tasks = []
        i = 0
        for line in rawfile.splitlines():
            i += 1 # To start task_id a 1
            tasks.append(Task(i, line))

        return tasks

    def _get_tasks(self, tasks, project = None, context = None, priority = None, complete=None):
        valid_tasks = []
        for t in tasks:
            if (project is None or project in t.project) \
               and (context is None or context in t.context) \
               and (complete is None or complete == t.complete):
               valid_tasks.append(t)

        return valid_tasks

# Code greatly inspired from https://github.com/dirkolbrich/todotxt/blob/master/todotxt/task.py
class Task (object):
    '''A single Task object.'''

    _DATE_REGEX = r'\d{4}-[0-1]\d-[0-3]\d'
    _PRIORITY_REGEX = r'(?P<priority>^\([A-Z]\))'
    _PROJECT_REGEX = r'(?P<project>[+][^\s]+)'
    _CONTEXT_REGEX = r'(?P<context>@[^\s]+)'
    _COMPLETED_REGEX = r'(?P<completed>^x)'
    _DUE_DATE_REGEX = r'(?P<dueDate>due:' + _DATE_REGEX + ')'
    _KEY_VALUE_REGEX = r'(?P<key>[^:\s]+):{1}(?P<value>[^:\s])+'

    def __init__(self, task_id='', raw=''):
        '''Initiate the Task object.'''
        self.raw = raw
        self.task_id = task_id
        self.task = ''
        self.priority = None
        self.project = []
        self.context = []
        self.creation_date = None
        self.complete = False
        self.completion_date = None
        self.due_date = None

        self.decode(self.raw)

    def decode(self, line):
        '''Decode the raw task text.'''

        # split line into parts, separated by white space
        parts = line.split(' ')
        # parse each part of line
        i = 0
        while i < len(parts):
            self.parse(parts[i], i)
            i += 1
        print(parts, len(parts))

        tmp = []
        for part in parts:
            if re.search(self._PRIORITY_REGEX, part) is None \
                and re.search(self._COMPLETED_REGEX, part) is None \
                and re.search(self._PROJECT_REGEX, part) is None \
                and re.search(self._PRIORITY_REGEX, part) is None \
                and re.search(self._DATE_REGEX, part) is None \
                and re.search(self._CONTEXT_REGEX, part) is None:
                tmp.append(part)

        self.task = ' '.join(tmp)


    def parse(self, part, index):
        '''Parse each single part of the text line.'''

        # parse first part in line
        if index == 0:
            # parse completed task
            if part == 'x':
                self.complete = True
            # parse priority
            elif re.search(self._PRIORITY_REGEX, part):
                self.priority = part[1]
            # parse creation date
            elif re.search(self._DATE_REGEX, part):
                self.creation_date = part

        # parse for second part in line
        if index == 1:
            # parse for creation date
            if self.priority is not None and re.search(self._DATE_REGEX, part):
                self.creation_date = part
            # parse for completion date
            elif self.complete and re.search(self._DATE_REGEX, part):
                self.completion_date = part

        if index == 2:
            # parse for creation date if a completion date was also found
            if self.complete and re.search(self._DATE_REGEX, part):
                self.creation_date = part

        # parse parts longer than 1
        if len(part) > 1:
            # parse for project
            if part.startswith('+'):
                self.project.append(part[1:])
            # parse for context
            elif part.startswith('@'):
                self.context.append(part[1:])
            # parse for due date
            elif part.startswith('due:'):
                self.due_date = part[4:]

    def encode(self):
        '''Encode the Task object to a raw text line for todo.txt'''
        pass

