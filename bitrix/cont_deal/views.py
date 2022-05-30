from django.shortcuts import render
from django.http import HttpResponse
import requests
import json

#Для проверки скрипта зарегистрирован аккаунт в b24 https://b24-hprcr3.bitrix24.ru (пароль: 12345678X)
#Для формирования входного запроса на стартовой странице есть текстовое поле, для ввода туда входного запроса, а также его изменения
#токен доступа и точки входа в методы b24
auth = 'e7c294620000071b005baa0c00000001000007b63614110e6a0ac96913ae749155f06b'#токет доступа (действует 1 час). Получал из консоли в документации по REST API, выполняя тренировочные запросы
crm_deal_fields = 'https://b24-hprcr3.bitrix24.ru/rest/crm.deal.fields'
crm_deal_userfield_add = 'https://b24-hprcr3.bitrix24.ru/rest/crm.deal.userfield.add'
crm_contact_list = 'https://b24-hprcr3.bitrix24.ru/rest/crm.contact.list'
crm_deal_list = 'https://b24-hprcr3.bitrix24.ru/rest/crm.deal.list'
crm_contact_add = 'https://b24-hprcr3.bitrix24.ru/rest/crm.contact.add'
crm_deal_add = 'https://b24-hprcr3.bitrix24.ru/rest/crm.deal.add'
crm_deal_update = 'https://b24-hprcr3.bitrix24.ru/rest/crm.deal.update'


def start(request):
    return render(request, 'cont_deal/start.html')


def getreq(request):
    if request.method == "POST":
        response = json.loads(request.POST.get('name'))#ответ полученный из POST запроса, приведенный к словарю python

        exit = "" #строковая переменная для формирования результата запроса

        #Формирование новых полей
        fields_to_add, fields_all = to_add(response) #присваивание переменным результатов выполнения функции to_add() | поля для добавления, все поля из запроса
        for field in fields_to_add: #цикл добавляющий поля в b24 из списка сформированного функцией to_add()
            type = "string"
            params = {"auth": auth, "fields[FIELD_NAME]": field, "fields[USER_TYPE_ID]": type}#формируем параметры запроса
            requests.post(crm_deal_userfield_add, params=params) #запрос на формирование новых полей

        #Проверка контакта (новый или нет), если новый, то контакт добавляется в b24
        cont_new, _ = cont_is_new(response) #присваивание переменной cont_new результата выполнения функции
        if cont_new:#если контакт новый
            cont_req = {"auth": auth, "fields[NAME]": response["client"]["name"],
                    "fields[LAST_NAME]": response["client"]["surname"], "fields[PHONE][0][VALUE]": response["client"]["phone"],
                        "fields[ADDRESS]": response["client"]["adress"]}#формируем параметры запроса
            requests.post(crm_contact_add, params=cont_req)
            exit += "Добавлен новый контакт. "
        _, cont_ID = cont_is_new(response)#присваиваем переменной ID контакта после добавления нового или уже существующего

        #Проверка сделки (новая или нет, изменились поля или нет). В результате или добавляется новая сделка или изменяется существующая
        new_deal, deal_in_crm = deal_is_new(response) #распаковка результата вызова функции deal_is_new() | новая сделка, поля возвращенные b24
        if new_deal: #если сделка новая - создаем новую сделку и связываем ее с контактом.
            deal_req = {"auth": auth}
            for field in fields_all:#формируем параметры запроса с помощью цикла из списка всех полей
                deal_req["fields"+"["+field+"]"] = str(response[field.lower() if field.find("UF") == -1 else field.lower()[7:]])
            deal_req["fields[CONTACT_ID]"] = cont_ID #добавляем ID контакта для связывания сделки и контакта
            requests.post(crm_deal_add, params=deal_req)
            exit += "Добавлена новая сделка и привязана к контакту с ID = {}. ".format(cont_ID)
        else: #если сделка существует
            list_fields = ["UF_CRM_DELIVERY_ADRESS", "UF_CRM_DELIVERY_DATE", "UF_CRM_PRODUCTS"]#список полей которые нужно сверить
            fields_update = [] #список для формирования результата выполнения скрипта
            deal_update_req = {} #пустой словарь для формирования параметров запроса на изменение полей
            for field in list_fields: #в цикле формируем параметры запроса
                if str(response[field.lower()[7:]]) == str(deal_in_crm[0][field]):
                    continue #пропускаем поле, если не изменилось
                else:
                    deal_update_req["fields"+"["+field+"]"] = str(response[field.lower()[7:]])
                    fields_update.append(field)#добавляем в список поля которые изменились
            if  deal_update_req == dict(): #если все поля совпадают
                exit += "Сделка существует, исправления полей не требуется."
            else: #если есть изменившиеся поля
                deal_update_req["auth"] = auth #добавляем в параметры токен доступа
                deal_update_req["id"] = deal_in_crm[0]['ID'] #добавляем ID сделки для поиска
                requests.post(crm_deal_update, params=deal_update_req) #запрос к b24 на изменение полей
                exit += "Сделка существует, обновлены поля {}".format(str(fields_update))

    return HttpResponse(exit)


def to_add(response):#функция для формирования списка полей для добавления и всего списка полей
    deal_field = []
    for fields_deal in response.keys():#в цикле создаем список всех полей, пропуская поле client, а также переводим все в верхний регистр
        if fields_deal != "client":
            deal_field.append(fields_deal.upper())
    deal_fields_set = set(deal_field) #формируем множество полей запроса
    deal_crm_fields_req = {"auth": auth}#параметры запроса полей сделки из базы b24
    deal_crm_fields_set = set(requests.post(crm_deal_fields, params=deal_crm_fields_req).json()['result'].keys())#формируем множество всех полей сделки из b24 с помощью запроса
    deal_fields_add = deal_fields_set - deal_crm_fields_set #определяем поля которых нет во множестве полей из b24
    deal_f_add_UF_set = set(map(lambda x: "UF_CRM_" + x, deal_fields_add))#так как при добавлении пользовательского поля добавляется префикс UF_CRM_ добавляем префикс к полям
    deal_f_add_UF = list(deal_f_add_UF_set - deal_crm_fields_set)#снова определяем поля которых нет в множестве полей из b24, формируем список полей для добавления
    deal_fields_not_add = deal_fields_set - deal_fields_add #формируем множество полей которые не нужно добавлять
    deal_f_all = list(deal_fields_not_add.union(deal_f_add_UF_set))#объединяем множества и создаем список всех полей запроса
    return deal_f_add_UF, deal_f_all #список полей к добавлению, общий список полей


def cont_is_new(response): #функция для определения новый ли контакт, если контакт существует возвращает также ID контакта для связывания со сделкой
    cont_crm_req = {"auth": auth, "filter[PHONE]": response["client"]["phone"], "select[0]": "ID"}
    cont_crm = requests.post(crm_contact_list, params=cont_crm_req).json()
    if list(cont_crm['result']) == list():
        return True, "spam"
    else:
        return False, int(cont_crm['result'][0]['ID'])

def deal_is_new(response):#функция для определения новая ли сделка, а также возвращения всех необходимых полей
    deal_crm_req = {"auth": auth, "filter[=UF_CRM_DELIVERY_CODE]": response['delivery_code'],
     "select[0]":"ID", "select[1]": "UF_CRM_DELIVERY_ADRESS", "select[3]": "UF_CRM_DELIVERY_DATE", "select[4]": "UF_CRM_PRODUCTS"}
    deal_crm = requests.post(crm_deal_list, params=deal_crm_req).json()
    return list(deal_crm['result']) == list(), deal_crm['result']
