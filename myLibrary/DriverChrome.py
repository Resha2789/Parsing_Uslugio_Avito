import re

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.proxy import Proxy, ProxyType
from webdriver_manager.chrome import ChromeDriverManager
from myLibrary import ProxyCheck
from myLibrary import MainWindow
from datetime import datetime, timedelta
import time
import socket


# Запуск WebDriverChrome
# url='', proxy=None, browser=False
class StartDriver(ProxyCheck.ProxyCheck):
    def __init__(self, mainWindow=None, url='', proxy=None, browser=False):
        super().__init__()
        self.mainWindow = mainWindow
        m: MainWindow.MainWindow
        m = self.mainWindow

        self.driver = None
        self.show_browser = browser
        self.driver_closed = False
        self.set_url = url
        self.total_person = None
        self.time_out = 0

    def star_driver(self, url=None, proxy=True):
        m: MainWindow.MainWindow
        m = self.mainWindow

        if not m.parsing_uslugio:
            return

        self.set_url = url

        if self.driver is not None:
            try:
                print(f"DRIVER CLOSE")
                self.driver.close()
                time.sleep(4)
                self.driver = None
            except Exception as detail:
                self.driver = None
                print("ERROR DRIVER CLOSE:", detail)

        print(f"DRIVER START")
        options = self.options(proxy=proxy)

        try:
            # Запускаем webDriverChrome
            # socket.setdefaulttimeout(1)
            self.driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(), chrome_options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36'})
            self.driver.set_page_load_timeout(120)
            # Загружаем сайт по ссылке url
            self.driver.implicitly_wait(30)
            self.driver.get(url)

            print("Заргузка страницы успешна прошла.")
        except TimeoutException:
            print("Страница загрузилась не доконца.")
            return True


        except Exception as detail:
            # self.driver_closed = False
            print(f"ERROR star_driver: {self.set_url}", detail)
            print("Перезапускаем star_driver")
            return self.star_driver(url=self.set_url, proxy=proxy)

        return True

    # Timeout update website 5min
    def tim_out_thread(self):
        m: MainWindow.MainWindow
        m = self.mainWindow

        while m.parsing_uslugio:
            try:
                if not m.parsing_uslugio:
                    return
                if self.total_person != len(m.out_phone_number):
                    self.total_person = len(m.out_phone_number)
                    self.time_out = datetime.now() + timedelta(minutes=5)
                    print(f"START TIME_OUT_THREAD {str(self.time_out)}")

                if datetime.now() > self.time_out:
                    self.time_out = datetime.now() + timedelta(minutes=5)
                    if self.driver is not None:
                        print(f"TIME_OUT_THREAD!")
                        self.driver.close()
                        # Посылаем сигнал на главное окно для презагрузки потока
                        m.Commun.uslugio_restart_thread.emit({'data': True})
                time.sleep(5)

            except Exception as detail:
                print(f"ERROR tim_out_thread:", detail)
                print("Перезапускаем tim_out_thread")
                self.driver = None

                if m.parsing_uslugio:
                    return self.tim_out_thread()
                else:
                    return

        return

    def options(self, proxy=True):
        m: MainWindow.MainWindow
        m = self.mainWindow

        # Устанавливаем опции для webdriverChrome
        options = webdriver.ChromeOptions()

        prefs = {'profile.default_content_setting_values': {'cookies': 2, 'images': 2,
                                                            'plugins': 2, 'popups': 2, 'geolocation': 2,
                                                            'notifications': 2, 'auto_select_certificate': 2, 'fullscreen': 2,
                                                            'mouselock': 2, 'mixed_script': 2, 'media_stream': 2,
                                                            'media_stream_mic': 2, 'media_stream_camera': 2, 'protocol_handlers': 2,
                                                            'ppapi_broker': 2, 'automatic_downloads': 2, 'midi_sysex': 2,
                                                            'push_messaging': 2, 'ssl_cert_decisions': 2, 'metro_switch_to_desktop': 2,
                                                            'protected_media_identifier': 2, 'app_banner': 2, 'site_engagement': 2,
                                                            'durable_storage': 2}}

        options.add_experimental_option('prefs', prefs)
        options.add_argument("disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("ignore-certificate-errors")
        # Развернуть на весь экран
        options.add_argument("start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        # Утсанавливаем запрет на загрузку изоброжении
        options.add_argument('--blink-settings=imagesEnabled=false')
        # Показать браузер
        if not self.show_browser:
            # Не показываем веб браузер
            options.add_argument('headless')

        if proxy:
            while len(m.uslugio_verified_proxies) == 0:
                if not m.parsing_uslugio:
                    return
                print(f"Ждем прокси...")
                time.sleep(2)
            else:
                print(f"Опция proxy-server {m.uslugio_verified_proxies[0]}")
                # options.add_argument('--proxy-server=%s' % m.uslugio_verified_proxies[0])
                # m.uslugio_used_proxies.append(m.uslugio_verified_proxies[0])
                # m.uslugio_verified_proxies = m.uslugio_verified_proxies[1:]
                m.Commun.uslugio_proxy_update.emit(m.uslugio_verified_proxies)

        return options


class Execute(StartDriver):
    def __init__(self, mainWindow=None, url='', proxy=None, browser=False, js=''):
        super().__init__(mainWindow=mainWindow, url=url, proxy=proxy, browser=browser)
        self.mainWindow = mainWindow
        self.count_recurs = 0
        self.js = js

    # Добавляем на страницу свою библиотеку js
    def set_library(self):
        m: MainWindow.MainWindow
        m = self.mainWindow

        if not m.parsing_uslugio:
            return

        try:
            # Считываем скрипты
            library_js = open(self.js, 'r', encoding='utf-8').read()

            # Устанавливаем в нутри <body> последним элемент <script> </script> </body>
            # time.sleep(5)  # Останавливаем дальнейшее выполнения кода на 5 секунд

            # Внедряем скрирт set_library(data) в веб страницу
            self.driver.execute_script("""      
                script_set_library = function set_library(data) {
                        if ($('body').length != 0) {
                            var scr = document.createElement('script');
                            scr.textContent = data;
                            document.body.appendChild(scr);

                            return true;
                        }
                            return false;
                        }

                var scr = document.createElement('script');
                scr.textContent = script_set_library;
                document.body.appendChild(scr);
                
                script_check_function = function check_function(array){
                            var data = [];
                            for (var i = 0; i < array.length; i++) {
                                if (new Function('return typeof ' + array[i])() !== 'undefined') {
                                    console.log('Функция с именем ' + array[i] + ' существует!')
                                }
                                else{
                                    console.log('Функция с именем ' + array[i] + 'НЕ СУЩЕСТВУЕТ!')
                                    data.push(array[i]);
                                }
                            }
                            return data;
                        }
                
                scr = document.createElement('script');
                scr.textContent = script_check_function;
                document.body.appendChild(scr);
                
                if (!window.jQuery){
                    scr = document.createElement('script');
                    scr.type = 'text/javascript';
                    scr.src = 'https://code.jquery.com/jquery-3.6.0.min.js';
                    document.head.appendChild(scr);
                }
            """)

            # Запускаем ранее внедренный скрипт set_library(data)
            self.execute_js(tr=1, sl=1, data=f"set_library({[library_js]})")

            data = re.findall(r'function\s+(\w+)[(]', library_js)
            js_functions = self.execute_js(tr=0, sl=1, rt=True, data=f"check_function({data})")

            if type(js_functions) == list and len(js_functions) > 0:
                for i in js_functions:
                    print(f"Не найден {i}")
                raise Exception("Не все скрепты были внедрены на вебстраницу!")
            print(f"Все скрипты установлены")

            return True

        except FileNotFoundError:
            print(f'Файл скрипты не найден {self.js}')
            return False

        except Exception as detail:
            print("ERROR set_library:", detail)
            if m.parsing_uslugio:
                return self.star_driver(url=self.set_url)
            else:
                return

    # js_execute запускает внедренные скрипты на странице и получает от них ответ
    def execute_js(self, tr=0, sl=0, rt=False, t=0, exit_loop=False, data=None):
        """
        :param tr: int Количество рекурсией (количество попыток найти элемент)
        :param sl: int Количество секунд ожидать перед выполнения кода
        :param rt: Если параметр rt = True то возвращам полученый от скрипта значение
        :param t: Если элемент не найден то вернуть: 0 - Данных нет; 1 - 0; 2 - False;
        :param exit_loop: Если метод вызван внутри цикла то exit_loop=True завершит цикл
        :param data: Название скрипта
        :return: Возвращает ответ если rt=True
        """
        if sl > 0:
            time.sleep(sl)  # Засыпаем

        try:
            # Запускаем javaScript в браузере и получаем результат
            result = self.driver.execute_script(f"return {data}")
        except Exception as detail:
            print(f"EXCEPT execute_js: {data}")
            print("ERROR:", detail)
            if exit_loop:
                print("ERROR:", detail)
                return 'not execute'
            else:
                return self.star_driver(url=self.set_url)  # Рекурсия с темеже параметрами

        # Если результа False и count_recurs < tr засыпаем на 2 сек. и запускаем рекурсию (рекурсия на случие если элемент не успел появится)
        if not result and self.count_recurs < tr:
            time.sleep(2)
            self.count_recurs += 1  # Увеличиваем счетчик рекурсии на +1
            return self.execute_js(tr=tr, sl=0, rt=rt, t=t, data=data)  # Рекурсия с темеже параметрами

        # Результат False то возвращам по условию значение (Данных нет, 0, False)
        if not result:
            if t == 0:
                result = 'Данных нет'
            if t == 1:
                result = 0
            if t == 2:
                result = False

        # Обнуляем счетчик количество рекурсии
        self.count_recurs = 0

        # Если параметр rt = True то возвращам полученый от скрипта значение
        if rt:
            return result
