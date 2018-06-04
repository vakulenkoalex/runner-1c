import os

import runner1c
import runner1c.commands.start
import runner1c.common as common
import runner1c.exit_code as exit_code


class AddExtensionsParser(runner1c.parser.Parser):
    @property
    def name(self):
        return 'add_extensions'

    @property
    def description(self):
        return 'добавление расширений в конфигурацию'

    # noinspection PyMethodMayBeStatic
    def create_handler(self, **kwargs):
        return AddExtensions(**kwargs)

    def set_up(self):
        self.add_argument_to_parser()
        self._parser.add_argument('--folder', required=True, help='каталог, содержащий исходники расширения '
                                                                  'конфигурации')


class AddExtensions(runner1c.command.Command):
    def execute(self):
        return_code = runner1c.exit_code.EXIT_CODE.error
        extensions_name = self._get_extensions_name()

        self.start_agent()

        # noinspection PyPep8,PyBroadException
        try:
            for name in extensions_name:
                command = 'config load-files --dir "{}" --extension {}'
                return_code = self.send_to_agent(command.format(os.path.join(self.arguments.folder, name), name))
                if not exit_code.success_result(return_code):
                    break
                command = 'config update-db-cfg --extension {}'
                return_code = self.send_to_agent(command.format(name))
                if not exit_code.success_result(return_code):
                    break
        except:
            return_code = runner1c.exit_code.EXIT_CODE.error
        finally:
            self.close_agent()

        if exit_code.success_result(return_code):
            p_start = runner1c.command.EmptyParameters(self.arguments)
            setattr(p_start, 'connection', self.arguments.connection)
            setattr(p_start, 'epf', common.get_path_to_project(os.path.join('build',
                                                                            'tools',
                                                                            'epf',
                                                                            'ChangeSafeModeForExtension.epf')))
            return_code = runner1c.commands.start.Start(arguments=p_start).execute()

        return return_code

    def _get_extensions_name(self):
        return os.listdir(self.arguments.folder)
