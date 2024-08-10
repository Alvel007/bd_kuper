import configparser
import requests
import time
import threading
import re

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options

config = configparser.ConfigParser(interpolation=None)
config.read('config.ini')


kuper_token_str = config.get('settings', 'kuper_token')
kuper_token = eval(kuper_token_str)
visible = config.getboolean('settings', 'visible')
tg_message = config.getboolean('settings', 'tg_message')
bot_token = config.get('settings', 'bot_token')
chat_id = config.get('settings', 'chat_id')
check_time = int(config.get('settings', 'check_time'))


def tg_alert(alarm):
    """Функция отправки сообщения в чат через бота telegram"""
    return requests.get(f'https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&parse_mode=html&text={alarm}')

def extract_text(driver, tag):
    """Функция получения текста на странице по тегу"""
    wait = WebDriverWait(driver, 10)
    element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, tag)))
    return element.text

def button_click(driver, sleep, tag1, tag2): 
    """Клай по кнопке внутри блока"""
    time.sleep(sleep)
    order_element = driver.find_element(By.CLASS_NAME, tag1)
    order_repeat = order_element.find_element(By.CLASS_NAME, tag2)
    time.sleep(1)
    return order_repeat.click()

def check_kuper(sm_token):
    driver = webdriver.Chrome()
    driver.get('https://kuper.ru/')
    driver.maximize_window()
    cookie = {'name': 'remember_user_token', 'value': sm_token}
    driver.add_cookie(cookie)
    driver.get('https://kuper.ru/user/edit')
    wait_banner = WebDriverWait(driver, 10)
    button_element = wait_banner.until(EC.presence_of_element_located((By.CLASS_NAME, "Popover_closeButton__r_I0_")))
    button_element.click()
    phone_number = re.sub(r'\D', '', extract_text(driver, 'UserEditField_value__eb_6x'))
    driver.get('https://kuper.ru/user/shipments')
    order = extract_text(driver, 'styles_number__qfkjG')
    driver.get(f'https://kuper.ru/user/shipments/{order}')
    address = (extract_text(driver, "styles_textLarge__mF4VC"))
    sum_element = driver.find_element(By.CSS_SELECTOR, "[data-qa='user-shipment-total'].styles_detailsText__hw0B5")
    total = sum_element.text
    time_delivery = (extract_text(driver, 'NewShipmentState_time__aDFCI'))

    count_chek = 1
    count_completed = 1
    count_assembly = 1
    count_delivery = 1
    empty_count = 0

    while True:
        driver.refresh()
        time.sleep(1.5)
        try:
            status_ord = None
            status_elements = driver.find_elements(By.CLASS_NAME, "NewShipmentState_stateListItemName__LonPy")
            
            if len(status_elements) == 0:
                empty_count += 1
                if empty_count == 2:
                    break
                time.sleep(60)
                continue
            else:
                empty_count = 0

            for status in status_elements:
                if status.text.strip():
                    status_ord = status.text
                    break
            if count_chek == 1:
                message = (f'{phone_number}, {order}, {address}, {time_delivery}, {total}, {status_ord}')
                print(message)
                if tg_message:
                    tg_alert(message)
                count_chek = 2

            if status_ord == 'Собираем' and count_assembly == 1:
                message = (f'{order}, {status_ord}')
                print(message)
                if tg_message:
                    tg_alert(message)
                count_assembly = 2

            if status_ord == 'Скоро отправим' and count_completed == 1:
                sum_element = driver.find_element(By.CSS_SELECTOR, "[data-qa='user-shipment-total'].styles_detailsText__hw0B5")
                total = sum_element.text
                message = (f'{order}, {status_ord}, {total}')
                print(message)
                if tg_message:
                    tg_alert(message)
                count_completed = 2

            if status_ord == 'В пути' and count_delivery == 1:
                time.sleep(1)
                buttons_block = driver.find_element(By.CLASS_NAME, "ButtonsBlock_buttons__NgmLE")
                courier_str = buttons_block.find_element(By.TAG_NAME, "a").text
                courier_tel = re.sub(r'\D', '', courier_str)
                print(f'Курьер {courier_tel}')
                time_delivery = (extract_text(driver, 'NewShipmentState_time__aDFCI'))
                message = (f'{order}, {address}, {status_ord}, курьер: {courier_tel}, {time_delivery}')
                print(message)
                if tg_message:
                    tg_alert(message)
                count_delivery = 2

            time.sleep(check_time)
        except TimeoutException:
            print(f'Возникла ошибка при обработке заказа {order}.')
            break

    try:
        button_click(driver, 2, tag1 ='styles_container__M86q3', tag2 ='_BodyMN_1di36_25') 
        button_click(driver, 2, tag1 ='RepeatUserShipmentModal_buttons__O30Wq', tag2 ='Button_default__riDte') 
        button_click(driver, 15, tag1 ='CartContainer_root__7KdAU', tag2 ='CartButton_text___VnWt') 
        button_click(driver, 10, tag1 ='CookiesConcent_root__ElxL4', tag2 ='CookiesConcent_btnLabel__qaDH1') 
        button_click(driver, 4, tag1 ='PayMethodCard_row__YABpi', tag2 ='Button_root__100C6')
        wait = WebDriverWait(driver, 15)
        element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'Modal_header__10KZF')))
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        button = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "PaymentMethodDeleteButton_root__6fE2_")))
        button.click()
        message = (f'{phone_number} карта удалена из аккаунта')
        print(message)
        if tg_message:
            tg_alert(message)
    except:
        message = (f'{phone_number}. Ошибка при удалении карты. Удалите вручную.')
        print(message)
        if tg_message:
            tg_alert(message)

    time.sleep(200)
    driver.quit()

def main(kuper_tokens):
    threads = []
    for i, token in enumerate(kuper_tokens):
        thread = threading.Thread(target=check_kuper, args=(token,))
        threads.append(thread)
        thread.start()
        time.sleep(10)

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    kuper_tokens = kuper_token
    main(kuper_tokens)

