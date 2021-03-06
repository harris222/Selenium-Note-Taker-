"""
    Title: knowItAll.pyT
    Author: Harris Zheng
    Description: Save Words Selected By User On The Web
"""
import logging
import sys
import signal
import time
import datetime
import atexit
import re
import keyboard
import threading
import os
from collections import defaultdict
from selenium.common.exceptions import NoSuchElementException, WebDriverException, \
NoSuchWindowException, ElementNotInteractableException, JavascriptException

import keyHandler
import variables
import ChromeDriver

## Globals
ROOT_PATH = "C:/Users/harri/Documents/Programming/Pure_Skills/Python/SeleniumDriver/Knowledge_selector/"
KNOWLEDGE_PATH = "./Knowledge"

def logException():
    '''
        Log Exceptions
    '''
    logging.exception("-------------------------------------------------------\nException Occured")

def processText(text : str):
    '''
        Process Text
        @param text: Process highlighted text. 
    '''
    text = re.sub("[\\t\\n\\r]+", " ", text).strip() ## Remove line breaks, tabs, and spaces  
    text = re.sub("[\.\,]$", "", text) ## remove punctuations at the end of a string
    text = text[0:1].upper() + text[1:] ## Upper case first letter.
    return text 

def isAddTextValid(prevText, text, learnedDetails):

    '''
        Title: isAddTextValid
        Context: @prevText -- text found 0.5 seconds before @text is found.
                 @learnedDetails -- List of knowledge that are already selected.

        Description: Finds prevText at 0-0.5 seconds, and finds text in 0.5s-1s. 
                     If text === prevText, text is added to learnedDetails. If not, text is not added
                     This ensures that text is only added to learnedDetails when it has been highlighted for a certain duration.       
    '''
    sameText = (prevText == text)
    notEmpty = (text != '')
    textAlreadyExists = False
    for item in learnedDetails:
        if item["detail"] == text:
            textAlreadyExists = True
            break  

    return sameText and notEmpty and not textAlreadyExists  
      
def findFileDirectory(ourFileName : str) -> str:
    '''
        @params : None
        return the path in which our notes will be saved.
    '''
    foundFile = False
    path = ROOT_PATH

    ## Find if ourFileName is an existing note
    for dirpath, dirnames, filenames in os.walk("./Knowledge"):
        print("Current dirpath : ", dirpath)
        print("Current files : ", filenames)
        for filename in filenames:
            ## If we find ourFileName inside the knowledge directory, then instead of writing .txt to root
            ## We write it to dirpath.
            if filename == ourFileName:
                path = dirpath
                foundFile = True
                break

        ## Do not continue walking if we have found file
        if foundFile: break
    
    return os.path.join(path, ourFileName)
    
def WriteOutlearnedDetails(focus, learnedDetails):
    '''
        Search for file with a certain name in the file directory. Then, write out knowledge in a text file.
        @param focus -- Title of text file. 
        @param learnedDetails -- Details learned, which are categorized in URLs. 
    '''
    print(focus, learnedDetails)
    ourFileName = focus + ".txt"
    currTime = datetime.datetime.now()
    strCurrentTime = currTime.strftime("%A %B %d, %Y -- %H:%M")
    path = findFileDirectory(ourFileName)
    print("Writing out to : ", path)
            
    
    ## Need a function to recurse through the directories and find the right file path.
    ## look into OS
    
    with open(path, "a+", encoding="utf-8") as f:
        
        ## For each url, write down its list of knowledge
        for url,knowledge in learnedDetails.items():
            if len(knowledge) != 0:
                f.write("--------------------- " + strCurrentTime + " ------------ " +  url  + "  ------------------------------------------------\n")
                for item in knowledge:
                    if (item["level"] != 0):
                        if item["level"] % 2 != 0:
                            f.write("\t" * item["level"] + "- ")
                        else:
                            f.write("\t" * item["level"] + "• ")
                    f.write(item["detail"] + "\n")
                f.write("\n")
        
def main():
    driver = ChromeDriver.ChromeDriver()
    LOG_FILENAME = "events.log"
    logging.basicConfig(filename=LOG_FILENAME, format="%(asctime)s", level=logging.ERROR, filemode='a')
    
    ## Test Website 
    prevText = ""
    currBaseText = ""
    level = 0
    fileKnowledge = defaultdict(list) # key -> ourFileName, value -> list of urlKnowledge 
    urlKnowledge = defaultdict(list) # key -> url, value -> list of highlighted text
    urlWindowNames = {}
    newWindowIndex = 0
    windowIndex = 0
    freeze = False

    focus = input("What is Your Focus?")
    
    keyThread = keyHandler.KeyThread(driver) 
    hotKeyThread = keyThread.activateHotKeys() ## You Must Return this thread to run multithreading?
    print(hotKeyThread)
    print("Thread Count: ", threading.active_count())
    
    while True:
        try: 
            url = driver.driver.current_url

            ## freeze loop
            while freeze:
                keyVariables = keyThread.updateMainThread()
                freeze = keyVariables["freeze"]
            
            time.sleep(0.5) ## Time it takes to find first instance of text: 0s - 0.5s 
            
            ### Case where we close tab left of current tab, and there are only two tabs.
            if newWindowIndex >= len(driver.driver.window_handles):
                newWindowIndex -= 1
                keyThread.updateKeyThread(windowIndex=newWindowIndex)

            driver.switch_to_new_tab(newWindowIndex) 
            
            text, baseText = driver.getSelectedText()
            text = processText(text)         

            ## How to update newWindowIndex? Without continuously
            keyThread.updateKeyThread(url, urlKnowledge, currBaseText, len(driver.driver.window_handles)) ## Make sure key is updated without empty url values
            
            ## Add Text if Valid
            if isAddTextValid(prevText, text, urlKnowledge[url]):
                urlKnowledge[url].append({"detail" : text, "level" : level})
                currBaseText = baseText
                keyThread.updateKeyThread(url, urlKnowledge, currBaseText, len(driver.driver.window_handles))

            ## Sync keyThread values with Main Thread Values
            keyVariables = keyThread.updateMainThread()
            currBaseText, url, urlKnowledge, level, newWindowIndex, freeze = [keyVariables["currBaseText"], keyVariables["url"], \
            keyVariables["urlKnowledge"], keyVariables["level"], keyVariables["windowIndex"], keyVariables["freeze"]]
            
            # print(str(level) + ". ")
            # for knowledge in urlKnowledge[url]:
            #     print(knowledge["detail"] + "\n")
                
            prevText = text
        except NoSuchWindowException:
            ## Usually the keythread updates the newWindowIndex variable,
            ## But here we update it in the mainthread, so we make sure newWindowIndex stay up to date
            ## and doesn't feed an invalid index to the 
            newWindowIndex = len(driver.driver.window_handles) - 1
            driver.switch_to_new_tab(len(driver.driver.window_handles) - 1)
            keyThread.updateKeyThread(windowIndex=newWindowIndex)
        except (KeyboardInterrupt, WebDriverException):
            WriteOutlearnedDetails(focus, urlKnowledge)
            logException()
            hotKeyThread.stop()
            sys.exit(0)
        

if __name__ == "__main__":
    main()

## After every chrome process, use Alt+F and X to Shut it Down For School 
                            
