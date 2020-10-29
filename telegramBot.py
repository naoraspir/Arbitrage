import requests

def send_msg(text):
    token="1183755020:AAF1kKHifI1MHIfX6ZJ50P-7vBjPOhw3qA4"
    chat_id="-382693075"

    url_req="https://api.telegram.org/bot"+token+"/sendMessage"+"?chat_id="+chat_id+"&text="+text
    results = requests.get(url_req)
