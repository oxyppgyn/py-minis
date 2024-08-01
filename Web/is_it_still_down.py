"""
Description: 
Checks the status of a downed webpage using and notifies you 
if the page's status code changes (i.e., the page is functional).

Version: 1.0.0
Created: 07/30/2024
Created by: Tanner Hammond
Python Version: 3.11.8
"""

import requests
import time
import winsound

def is_it_still_down(webpage: str, time_interval: int = 10, error_code: int = 500, audio: bool = True):
    """
    Continuously checks if a webpage is down and yells at you when it isn't.
    
    Params:
    * `webpage`: URL of webpage to check.
    * `time_interval`: how often to check the webpage (in minutes).
        * Default: `10`
    * `error_code`: Error code of the webpage you are trying to access.
        * Default: `500`
    * `audio`: Whether or not to play audio when the webpage is accessed.
        * Default: `True`
    """
    while True:
        response = requests.get(webpage)
        if response.status_code != error_code:
            break
        else:
            print('Still down  :(')
            time.sleep(time_interval*60)

    while True:
        print('Its up!     :)')
        if audio is True:
            winsound.Beep(1500, 2000)
        time.sleep(2)

#Usage

webpage = 'https://website.url'
check_interval = 10
is_it_still_down(webpage, 10)
