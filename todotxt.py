import logging
import re
import os.path

from kalliope.core.NeuronModule import NeuronModule, InvalidParameterException

logging.basicConfig()
logger = logging.getLogger("kalliope")

class Todotxt (NeuronModule):
    def __init__(self, **kwargs):
        super(Todotxt, self).__init__(**kwargs)

        self.configuration = {
            'action': kwargs.get('action', None),
            'todotxt_file': kwargs.get('todotxt_file', None),
            'priority': kwargs.get('priority', None),
            'project': kwargs.get('project', None),
            'context': kwargs.get('context', None),
            'complete': kwargs.get('complete', False),
            'content': kwargs.get('content', None),
            'due': kwargs.get('due', None)              # due date used instead or created/completion date because created date would imply a completion date from todotxt rules 
        }

        if self._is_parameters_ok():
            if self.configuration['action'] == "get":
                task_list = self._action_get()
                self.say({'action': self.configuration['action'], 'task_list': task_list, 'count': len(task_list)})

            elif self.configuration['action'] == "add":
                task = self._action_add()
                self.say({'action': self.configuration['action'], 'added_task': task})

            elif self.configuration['action'] == "del":
                count = self._action_del()
                self.say({'action': self.configuration['action'], 'count': count})
            elif self.configuration['action'] == "update":
                pass
            elif self.configuration['action'] == "send":
                pass


    def _action_get(self):
        # Parse file and get list of tasks
        tasks = self._get_tasks(self._parse_todotxt(self.configuration['todotxt_file']),
                                priority = self.configuration['priority'],
                                project = self.configuration['project'],
                                context = self.configuration['context'],
                                complete = self.configuration['complete'],
                                due = self.configuration['due'])

        task_list = []
        for t in tasks:
            task_list.append({
                'text': t.task,
                'priority': t.priority,
                'complete': t.complete,
                'due': t.due,
                'contexts': t.context,
                'projects': t.project,
            })

        return task_list

    def _action_add(self):
        task = Task()
        task.priority = self.configuration['priority']
        if self.configuration['project'] is not None:
            task.project.append(self.configuration['project'])
        if self.configuration['context'] is not None:
            task.context.append(self.configuration['context'])
        task.complete = self.configuration['complete']
        task.due = self.configuration['due']
        task.task = self.configuration['content']
        task.encode(task.task)

        self._add_task_line(self.configuration['todotxt_file'], task.raw)

        return task

    def _action_del(self):
        tmp_tasks = self._parse_todotxt(self.configuration['todotxt_file'])
        # Get all task(s)
        all_tasks = self._get_tasks(tmp_tasks)

        # Get task(s) to delete
        tasks_to_delete = self._get_tasks(tmp_tasks,
                                          priority = self.configuration['priority'],
                                          project = self.configuration['project'],
                                          context = self.configuration['context'],
                                          due = self.configuration['due'],
                                          complete = self.configuration['complete'])
        
        # Create final list of task to rewrite file
        count = 0
        raw_lines = []
        for t in all_tasks:
            if t not in tasks_to_delete:
                raw_lines.append(t.raw)
            else:
                count += 1

        # rewrite file
        self._rewrite_todofile(self.configuration['todotxt_file'], raw_lines)

        return count

    def _is_parameters_ok(self):
        """
        Check if received parameters are ok to perform operations in the neuron.
        :return: True if parameters are ok, raise an exception otherwise.
        .. raises:: MissingParameterException
        """
        if self.configuration['todotxt_file'] is None \
            or os.path.isfile(self.configuration['todotxt_file']) is False:
            raise InvalidParameterException("Todotxt need a valid and existing todo file")

        if self.configuration['action'] is None:
            raise InvalidParameterException("An action is require")

        if self.configuration['action'] == "add" and self.configuration['content'] is None:
            raise InvalidParameterException("A content is required when the action is add")

        return True
 
    def _rewrite_todofile(self, todofile, raw_lines):
        with open(todofile, 'w') as file:
            for line in raw_lines:
                file.write(line + "\n")
        

    def _add_task_line(self, todofile, line):
        logger.debug('todofile: %s - line: %s' % (todofile, line))
        with open(todofile, 'a') as file:
            file.write(line + "\n")

    def _parse_todotxt(self, todofile):
        with open(todofile, 'r') as file:
            rawfile = file.read()

        tasks = []
        i = 0
        for line in rawfile.splitlines():
            i += 1 # To start task_id a 1
            if len(line) > 1:
                tasks.append(Task(i, line))

        return tasks

    def _get_tasks(self, tasks, project = None, context = None, priority = None, complete=None, due=None):
        valid_tasks = []
        for t in tasks:
            if (project is None or project in t.project) \
               and (context is None or context in t.context) \
               and (due is None or due in t.due) \
               and (priority is None or priority in t.priority) \
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
        #print(parts, len(parts))

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

    def encode(self, content):
        '''Encode the Task object to a raw text line for todo.txt'''
        raw = ""
        if self.priority:
            raw += "(" + self.priority + ") "

        raw += self.task + " "

        for c in self.context:
            logger.debug(c)
            raw += "@" + c + " "

        for p in self.project:
            raw += "+" + p + " "

        self.raw = raw

