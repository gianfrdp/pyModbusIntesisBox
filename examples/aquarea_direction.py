from urllib.request import urlopen
import json

url = "http://192.168.4.45/status"
response = urlopen(url)
data_json = json.loads(response.read())
state = data_json["rollers"][0]["state"]
last_direction =  data_json["rollers"][0]["last_direction"]

print(F"state = {state}, last_direction = {last_direction}")

direction = None
if last_direction == state:
    direction = last_direction
else:
    direction = state

status = None
if direction == 'close':
    status = 'Climate'
elif direction == 'open':
    status = 'DHW'
else:
    status = 'Unknown'

print(F"status = {status}")