﻿
#Область ОбработчикиСобытийФормы

Процедура ПриОткрытии()
	
	Если Не ПустаяСтрока(ПараметрЗапуска) Тогда
		ОбработатьПараметрыЗапуска(ПараметрЗапуска);
	КонецЕсли;
	
	ПодключитьОбработчикОжидания("ПроверкаВыполненностиОбновления", ИнтервалОпроса());
	
КонецПроцедуры

#КонецОбласти

#Область СлужебныеПроцедурыИФункции

Процедура ПроверкаВыполненностиОбновления()
	
	Если Не ПрочитатьСобытиеЗавершенияОбновления() Тогда
		Возврат;
	КонецЕсли;
	
	Если Не ПустаяСтрока(ПутьКОбработкам) Тогда
		ОткрытьОбработку();
	КонецЕсли;
	
	ЗавершитьРаботуСистемы(Ложь);
	
КонецПроцедуры

Процедура ОбработатьПараметрыЗапуска(Знач Строка)
	ПутьКОбработкам = ПрочитатьПараметрыЗапуска(Строка);
КонецПроцедуры

Процедура ОткрытьОбработку()
	
	Для Каждого Файл Из НайтиФайлы(ПутьКОбработкам, "*.epf", Истина) Цикл
		Форма = ВнешниеОбработки.ПолучитьФорму(Файл.ПолноеИмя);
		Форма.Открыть();
	КонецЦикла;
	
КонецПроцедуры

#КонецОбласти

