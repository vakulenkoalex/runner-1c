import os
import re
import shutil
import tempfile

import runner1c
import runner1c.commands.diff_mxl
import runner1c.common as common
import runner1c.exit_code


class DumpConfigParser(runner1c.parser.Parser):
    @property
    def name(self):
        return 'dump_config'

    @property
    def description(self):
        return 'выгрузка конфигурации на исходники'

    # noinspection PyMethodMayBeStatic
    def create_handler(self, **kwargs):
        return DumpConfig(**kwargs)

    def set_up(self):
        self.add_argument_to_parser()
        self._parser.add_argument('--folder', required=True, help='каталог, в который будет выгружена конфигурация')
        self._parser.add_argument('--update', action='store_const', const=True, help='выгрузка изменений')
        self._parser.add_argument('--repair', action='store_const', const=True, help='исправлять ошибку платформы')


class DumpConfig(runner1c.command.Command):
    def __init__(self, **kwargs):
        kwargs['mode'] = runner1c.command.Mode.DESIGNER
        super().__init__(**kwargs)
        self.add_argument('/DumpConfigToFiles "{folder}" -Format Hierarchical')

        if getattr(self.arguments, 'update', False):
            # noinspection PyAttributeOutsideInit
            self._changes = tempfile.mktemp('.txt')
            self.add_argument('-update -force -getChanges {changes}')

            setattr(self.arguments, 'changes', self._changes)
            self.debug('changes "%s"', self._changes)

    def execute(self):
        if getattr(self.arguments, 'repair', False):
            copy_files = self._copy__files_with_error_to_tmp()

        if not getattr(self.arguments, 'update', False):
            common.clear_folder(self.arguments.folder)

        return_code = self.run()

        if return_code == runner1c.exit_code.EXIT_CODE.done:
            folders_for_scan = [self.arguments.folder]
            if getattr(self.arguments, 'update', False):
                text = self._read_changes()
                if text.find('FullDump') == -1:
                    folders_for_scan = self._get_change_bin_forms(text)

            if getattr(self.arguments, 'repair', False):
                repair_files = True
                if getattr(self.arguments, 'update', False):
                    # noinspection PyUnboundLocalVariable
                    repair_files = text.find('FullDump') > 0

                if repair_files:
                    self._delete_use_constant()
                    # noinspection PyUnboundLocalVariable
                    self._compare_file_with_error(copy_files)

            if len(folders_for_scan) > 0:
                self.get_module_ordinary_form(folders_for_scan)

        return return_code

    def _get_change_bin_forms(self, text):
        folders_for_scan = []
        forms = re.compile('.*\.Form.*\.Form', re.MULTILINE).findall(text)
        if len(forms) > 0:
            folders_for_scan = self._get_path_changed_forms(forms)
        return folders_for_scan

    def _read_changes(self):
        # noinspection PyUnboundLocalVariable
        with open(self._changes, mode='r', encoding='utf-8') as file:
            text = file.read()
        file.close()
        # noinspection PyUnboundLocalVariable
        common.delete_file(self._changes)
        return text

    def _compare_file_with_error(self, copy_files):
        self.debug('compare_file_with_error')
        origin_file_name = tempfile.mktemp('.txt')
        copy_file_name = tempfile.mktemp('.txt')
        result_file_name = tempfile.mktemp('.txt')
        with open(origin_file_name, mode='w', encoding='utf-8') as origin_file, \
                open(copy_file_name, mode='w', encoding='utf-8') as copy_file:
            for file, copy in copy_files.items():
                origin_file.write(file + '\n')
                copy_file.write(copy + '\n')
        origin_file.close()
        copy_file.close()

        p_diff_mxl = runner1c.command.EmptyParameters(self.arguments)
        setattr(p_diff_mxl, 'first', origin_file_name)
        setattr(p_diff_mxl, 'second', copy_file_name)
        setattr(p_diff_mxl, 'equal_files', result_file_name)
        return_code_diff = runner1c.commands.diff_mxl.DiffMxl(arguments=p_diff_mxl).execute()

        if return_code_diff == runner1c.exit_code.EXIT_CODE.done:
            with open(result_file_name, mode='r', encoding='utf-8-sig') as result_file:
                for line in result_file.readlines():
                    file = line.rstrip('\n')
                    copy = copy_files[file]
                    shutil.move(copy, file)
            result_file.close()

            common.delete_file(origin_file_name)
            common.delete_file(copy_file_name)
            common.delete_file(result_file_name)

        else:
            print('ошибка при сравнении файлов mxl платформой')

    def _copy__files_with_error_to_tmp(self):
        copy_files = {}
        for file in _get_files_with_error_in_dump():
            full_path = os.path.join(self.arguments.folder, file)
            if os.path.exists(full_path):
                copy = tempfile.mktemp('.xml')
                shutil.copy(full_path, copy)
                copy_files[full_path] = copy
        return copy_files

    def _get_path_changed_forms(self, forms):
        folders_for_scan = []
        for line in forms:
            parts = line.split(':')[1].split('.')
            class_name = parts[0]
            object_name = parts[1]
            form_name = parts[3]
            folders_for_scan.append(os.path.join(self.arguments.folder,
                                                 common.folder_for_class_1c(class_name),
                                                 object_name,
                                                 'Forms',
                                                 form_name))
        return folders_for_scan

    def _delete_use_constant(self):
        self.debug('delete_use_constant')
        for file_name in _get_files_with_constant():
            full_path = os.path.join(self.arguments.folder, file_name)
            if not os.path.exists(full_path):
                continue

            new_file = tempfile.mktemp('.xml')
            with open(full_path, mode='r', encoding='utf-8') as file, \
                    open(new_file, mode='w', encoding='utf-8') as copy_file:
                for line in file.readlines():
                    constant_exist = False
                    for constant in _get_constant_name():
                        if line.find("<Field>НаборКонстант.{}.Ref</Field>".format(constant)) > 0:
                            constant_exist = True
                            break
                    if not constant_exist:
                        copy_file.write(line)
            file.close()
            copy_file.close()
            shutil.move(new_file, full_path)


def _get_files_with_error_in_dump():
    return ["Reports\АнализЖурналаРегистрации\Templates\ПродолжительностьРаботыРегламентныхЗаданий\Ext\Template.xml"]


def _get_files_with_constant():
    # noinspection PyPep8
    return [
        "DataProcessors\НастройкаРазрешенийНаИспользованиеВнешнихРесурсов\Forms\НастройкиИспользованияПрофилейБезопасности\Ext\Form.xml",
        "DataProcessors\ПанельАдминистрированияБСП\Forms\НастройкиПользователейИПрав\Ext\Form.xml",
        "DataProcessors\ПанельАдминистрированияБСП\Forms\НастройкиРаботыСФайлами\Ext\Form.xml",
        "DataProcessors\ПанельАдминистрированияБСП\Forms\ОбщиеНастройки\Ext\Form.xml",
        "DataProcessors\ПанельАдминистрированияБСП\Forms\Органайзер\Ext\Form.xml",
        "DataProcessors\ПанельАдминистрированияБСП\Forms\ПечатныеФормыОтчетыИОбработки\Ext\Form.xml",
        "DataProcessors\ПанельАдминистрированияБСП\Forms\ПоддержкаИОбслуживание\Ext\Form.xml",
        "DataProcessors\ПанельАдминистрированияБСП\Forms\УправлениеПолнотекстовымПоискомИИзвлечениемТекстов\Ext\Form.xml"]


def _get_constant_name():
    return ["ДополнительнаяКолонкаПечатныхФормДокументов",
            "ПорядокПрисвоенияPLU",
            "СтратегияАвторезервированияНоменклатурыПоЗаказам",
            "СпособКонтроляДнейЗадолженности",
            "УказаниеЗаказовВТабличнойЧастиДокументов",
            "УказаниеСкладовВТабличнойЧастиДокументов",
            "ЮрФизЛицо",
            "ПровайдерSMS"]
