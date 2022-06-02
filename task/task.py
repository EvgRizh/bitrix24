import requests
from datetime import date, timedelta

#Для проверки скрипта зарегистрирован аккаунт в b24 https://b24-hprcr3.bitrix24.ru (пароль: 12345678X)
#Для формирования входного запроса на стартовой странице есть текстовое поле, для ввода туда входного запроса, а также его изменения
AUTH = 'e7c294620000071b005baa0c00000001000007b63614110e6a0ac96913ae749155f06b'#токет доступа (действует 1 час). Получал из консоли в документации по REST API, выполняя тренировочные запросы
date_holiday = {"2022-01-01": "Новый год",
                "2022-01-07": "Рождество",
                "2022-02-23": "День защитника отечества",
                "2022-03-08": "Международный женский день",
                "2022-05-01": "Праздник весны и труда",
                "2022-05-09": "День Победы",
                "2022-06-12": "День России",
                "2022-11-04": "День народного единства"
                }#словарь праздников
date_forward = date.today()+timedelta(3)#формируется дата сегодня + 3 дня
class Task: #класс задачи
    def __init__(self, title, resp_id):#конструктор принимающий на вход заголовок и ID ответственного
        self.title = title
        self.responsible_id = resp_id

    def set_fields(self, auth):
        return {"auth": auth, "fields[TITLE]": self.title, "fields[RESPONSIBLE_ID]": 1}#формируем параметры запроса, принимая на вход токен доступа

if str(date_forward) in date_holiday.keys():#проверка, есть ли сформированная дата в ключах словаря
    holiday = date_holiday[str(date_forward)]#получаем значение праздника по ключу
    fields = Task("Через 3 дня {}".format(holiday), 1)#создаем экземпляр задачи
    dict_fields = fields.set_fields(AUTH)#формируем параметры запроса
    response = requests.post('https://b24-hprcr3.bitrix24.ru/rest/tasks.task.add', params=dict_fields)#запрос на добавление задачи
    print(response.json())
