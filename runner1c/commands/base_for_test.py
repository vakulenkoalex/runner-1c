import asyncio
import os
import tempfile

import runner1c
import runner1c.commands.add_extensions as add_extensions
import runner1c.commands.load_config
import runner1c.commands.start
import runner1c.commands.sync as sync
import runner1c.common as common
import runner1c.exit_code as exit_code


class BaseForTestParser(runner1c.parser.Parser):
    @property
    def name(self):
        return 'base_for_test'

    @property
    def description(self):
        return 'создание базы из исходников для тестирования'

    # noinspection PyMethodMayBeStatic
    def create_handler(self, **kwargs):
        return BaseForTest(**kwargs)

    def set_up(self):
        self.add_argument_to_parser()
        self._parser.add_argument('--thick', action='store_const', const=True, help='толстый клиент')
        self._parser.add_argument('--folder', required=True, help='путь к папке с репозитарием')
        self._parser.add_argument('--create_epf', action='store_const', const=True, help='создать внешние '
                                                                                         'обработки репозитария')
        self._parser.add_argument('--create_cfe', action='store_const', const=True, help='загрузить расширения '
                                                                                         'репозитария')
        self._parser.add_argument('--create_tests', action='store_const', const=True, help='создать тесты репозитария')


async def start_enterprice(self, loop):
    p_start = runner1c.command.EmptyParameters(self.arguments)
    setattr(p_start, 'connection', self.arguments.connection)
    setattr(p_start, 'thick', self.arguments.thick)
    setattr(p_start, 'epf', common.get_path_to_project(os.path.join('runner1c',
                                                                    'build',
                                                                    'tools',
                                                                    'epf',
                                                                    'CloseAfterUpdate.epf')))

    path_to_fixtures = os.path.join(self.arguments.folder, 'build', 'spec', 'fixtures')
    if os.path.exists(path_to_fixtures):
        setattr(p_start, 'options', path_to_fixtures)

    call_string = runner1c.commands.start.Start(arguments=p_start).get_string_for_call()
    program, parameters = call_string.split(' ENTERPRISE')

    file_parameters = tempfile.mktemp('.txt')
    with open(file_parameters, mode='w', encoding='utf8') as file_parameters_stream:
        file_parameters_stream.write('ENTERPRISE ' + parameters)
    file_parameters_stream.close()

    cmd = program.replace('"', '')
    stdin = '/@ ' + file_parameters
    self.debug('create_subprocess_exec %s %s', cmd, stdin)
    process = await asyncio.create_subprocess_exec(cmd, stdin, loop=loop)

    await process.wait()

    common.delete_file(file_parameters)


async def start_designer(self):
    p_sync = runner1c.command.EmptyParameters(self.arguments)
    setattr(p_sync, 'connection', self.arguments.connection)
    setattr(p_sync, 'folder', self.arguments.folder)
    setattr(p_sync, 'create', True)
    setattr(p_sync, 'include', os.path.join(p_sync.folder, 'lib', 'epf'))
    setattr(p_sync, 'exclude', os.path.join(p_sync.folder, 'spec', 'fixtures'))
    sync.Sync(arguments=p_sync, agent_channel=self.get_agent_channel()).execute()


async def create_test(self):
    p_sync = runner1c.command.EmptyParameters(self.arguments)
    setattr(p_sync, 'folder', self.arguments.folder)
    setattr(p_sync, 'create', True)
    setattr(p_sync, 'include', os.path.join(p_sync.folder, 'spec'))
    setattr(p_sync, 'exclude', os.path.join(p_sync.folder, 'spec', 'fixtures'))
    setattr(p_sync, 'hash_file', 'D:\\1.txt')
    sync.Sync(arguments=p_sync).execute()


async def create_base(self):
    folder_for_config_src = 'cf'

    p_create = runner1c.command.EmptyParameters(self.arguments)
    setattr(p_create, 'connection', self.arguments.connection)
    return_code = runner1c.command.CreateBase(arguments=p_create).execute()

    if exit_code.success_result(return_code):

        self.start_agent()

        # noinspection PyPep8,PyBroadException
        try:
            command = 'config load-files --dir "{}" --update-config-dump-info'
            return_code = self.send_to_agent(command.format(os.path.join(self.arguments.folder,
                                                                         folder_for_config_src)))
            if exit_code.success_result(return_code):
                return_code = self.send_to_agent('config update-db-cfg')

                if exit_code.success_result(return_code):

                    if getattr(self.arguments, 'create_cfe', False):
                        p_extensions = runner1c.command.EmptyParameters(self.arguments)
                        setattr(p_extensions, 'connection', self.arguments.connection)
                        setattr(p_extensions, 'folder', os.path.join(self.arguments.folder, 'lib', 'ext'))
                        add_extensions.AddExtensions(arguments=p_extensions,
                                                     agent_channel=self.get_agent_channel()).execute()

                    if getattr(self.arguments, 'create_epf', False):
                        p_sync = runner1c.command.EmptyParameters(self.arguments)
                        setattr(p_sync, 'connection', self.arguments.connection)
                        setattr(p_sync, 'folder', self.arguments.folder)
                        setattr(p_sync, 'create', True)
                        setattr(p_sync, 'include', os.path.join(p_sync.folder, 'spec', 'fixtures'))
                        return_code = sync.Sync(arguments=p_sync, agent_channel=self.get_agent_channel()).execute()

                    if exit_code.success_result(return_code):
                        loop = asyncio.ProactorEventLoop()
                        asyncio.set_event_loop(loop)

                        tasks = []
                        if getattr(self.arguments, 'create_epf', False):
                            tasks.append(start_designer(self))
                        tasks.append(start_enterprice(self, loop))

                        loop.run_until_complete(asyncio.wait(tasks))
                        loop.close()

        except Exception as exception:
            self.error(exception)
            return_code = runner1c.exit_code.EXIT_CODE.error
        finally:
            self.close_agent()


class BaseForTest(runner1c.command.Command):
    def execute(self):
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)

        tasks = []
        if getattr(self.arguments, 'create_tests', False):
            tasks.append(create_test(self))
        tasks.append(create_base(self))

        loop.run_until_complete(asyncio.wait(tasks))
        loop.close()
