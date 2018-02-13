import os
import shutil
import tempfile

import runner1c


class PlatformCheckParser(runner1c.parser.Parser):
    @property
    def name(self):
        return 'platform_check'

    @property
    def description(self):
        return 'проверка конфигурации'

    # noinspection PyMethodMayBeStatic
    def execute(self, parameters):
        return PlatformCheckConfig(parameters).execute()

    def set_up(self):
        self.add_argument_to_parser()
        self._parser.add_argument('--options', required=True, help='опции проверки. Указываются с "-" и '
                                                                   'как в справке 1с')
        self._parser.add_argument('--skip_error', help='путь к файлу с ошибками-исключениями')
        self._parser.add_argument('--skip_object', help='путь к файлу с объектами, в которых ошибки игнорируются')
        self._parser.add_argument('--skip_modality', help='путь к файлу с объектами, в которых игнорируются ошибки '
                                                          'модальных вызовов')


class PlatformCheckConfig(runner1c.command.Command):
    def execute(self):
        builder = runner1c.cmd_string.CmdString(mode=runner1c.cmd_string.Mode.DESIGNER, parameters=self._parameters)
        builder.add_string('/CheckConfig {options}')

        setattr(self._parameters, 'cmd', builder.get_string())
        return_code = self.start()

        _delete_plug_function(self._parameters.log)

        if getattr(self._parameters, 'skip_modality'):
            _delete_modality_error(self._parameters.skip_modality, self._parameters.log)

        if getattr(self._parameters, 'skip_object'):
            _delete_skip_object(self._parameters.skip_object, self._parameters.log)

        if getattr(self._parameters, 'skip_error'):
            _delete_skip_error(self._parameters.skip_error, self._parameters.log)

        return return_code


def _delete_plug_function(log):
    unreference_procedure_error = 'Не обнаружено ссылок на'
    procedure_name_connectable = 'Подключаемый_'
    procedure_name_upload = 'ЗагрузитьИзТабличногоДокумента'

    new_log_file = tempfile.mktemp('.txt')
    new_log_file_stream = open(new_log_file, mode='w', encoding='utf-8')

    log_file = open(log, mode='r', encoding='utf-8')
    for line in log_file:
        if (unreference_procedure_error not in line) or \
                ((procedure_name_connectable not in line) and (procedure_name_upload not in line)):
            new_log_file_stream.write(line)

    log_file.close()
    new_log_file_stream.close()
    shutil.move(new_log_file, log)


def _read_file_to_list(file_name):
    file_stream = open(file_name, mode='r', encoding='utf-8')
    lines = file_stream.readlines()
    file_stream.close()

    return lines


def _delete_modality_error(skip_modality, log):
    if not os.path.exists(skip_modality):
        return

    modality_error = 'Использование модального вызова'

    modality_lines = _read_file_to_list(skip_modality)

    new_log_file = tempfile.mktemp('.txt')
    new_log_file_stream = open(new_log_file, mode='w', encoding='utf-8')

    log_file = open(log, mode='r', encoding='utf-8')
    for line in log_file:
        add_string = True
        if modality_error in line:
            for error_line in modality_lines:
                if error_line.strip() in line:
                    add_string = False
                    break
        if add_string:
            new_log_file_stream.write(line)

    log_file.close()
    new_log_file_stream.close()
    shutil.move(new_log_file, log)


def _delete_skip_object(skip_object, log):
    if not os.path.exists(skip_object):
        return

    skip_lines = _read_file_to_list(skip_object)

    new_log_file = tempfile.mktemp('.txt')
    new_log_file_stream = open(new_log_file, mode='w', encoding='utf-8')

    log_file = open(log, mode='r', encoding='utf-8')
    for line in log_file:
        add_string = True
        for error_line in skip_lines:
            if error_line.strip() in line:
                add_string = False
                break
        if add_string:
            new_log_file_stream.write(line)

    log_file.close()
    new_log_file_stream.close()
    shutil.move(new_log_file, log)


def _delete_skip_error(skip_error, log):
    if not os.path.exists(skip_error):
        return

    skip_lines = _read_file_to_list(skip_error)
    skip_lines.append('Ошибок не обнаружено\n')

    new_log_file = tempfile.mktemp('.txt')
    new_log_file_stream = open(new_log_file, mode='w', encoding='utf-8')

    log_file = open(log, mode='r', encoding='utf-8')
    for line in log_file:
        add_string = True
        for error_line in skip_lines:
            if error_line.strip() in line:
                add_string = False
                break
        if add_string:
            new_log_file_stream.write(line)

    log_file.close()
    new_log_file_stream.close()
    shutil.move(new_log_file, log)