import os
import pyttsx3
import speech_recognition as sr
import AppOpener
import urllib
import wmi
import psutil
import signal
import requests
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from word2number import w2n
from openai import OpenAI
import pyautogui
import eel
import sqlite3  # Import SQLite3
import threading
import webbrowser
import pygetwindow as gw
import time

# Initialize Eel
eel.init("web")

# API Keys
DEEPSEEK_API_KEY = ""
WEATHERAPI_KEY = ""
MEDIASTACK_API_KEY = ""  # Replace with your Mediastack API key

# Initialize DeepSeek Client
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://openrouter.ai/api/v1")

# Volume Control
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))


# SQLite3 Database Setup
def initialize_db():
    """Initialize the SQLite database and create the chat_history table if it doesn't exist."""
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def initialize_db2():
    conn = sqlite3.connect("stored_websites.db")
    cursor = conn.cursor()
    cursor.execute("""
                   create table if not exists stored_websites (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   web_name TEXT NOT NULL,
                   web_url TEXT NOT NULL,
                   timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                   )
                  """)
    conn.commit()
    conn.close()


# Initialize the database
initialize_db()
initialize_db2()

@eel.expose
def save_to_db2(web_name, web_url):
    """Save website name and URL into the stored_websites.db database."""
    try:
        conn = sqlite3.connect("stored_websites.db")
        cursor = conn.cursor()

        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stored_websites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                web_name TEXT NOT NULL,
                web_url TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(web_name, web_url)
            )
        """)

        # Insert the website details
        cursor.execute("INSERT INTO stored_websites (web_name, web_url) VALUES (?, ?)", 
                      (web_name, web_url))
        
        conn.commit()
        return {"success": True, "message": "Website saved successfully!"}

    except sqlite3.IntegrityError:
        return {"success": False, "error": "Website already exists in the database."}
    except Exception as e:
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        if conn:
            conn.close()

@eel.expose
def save_to_db(query, response):
    """Save a query and response to the SQLite database."""
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (query, response) VALUES (?, ?)", (query, response))
    conn.commit()
    conn.close()


@eel.expose()
def get_chat_history_from_db():

    """Retrieve the chat history from the SQLite database."""
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT query, response FROM chat_history ORDER BY timestamp DESC")
    history = cursor.fetchall()
    conn.close()
    return [{"query": item[0], "response": item[1]} for item in history]




@eel.expose
def get_webinfo(web_name):
    """Get all stored websites from the database"""
    try:
        conn = sqlite3.connect("stored_websites.db")
        cursor = conn.cursor()
        
        # Get all websites (pass web_name as a tuple)
        cursor.execute(
            "SELECT web_url FROM stored_websites WHERE web_name = ? ORDER BY timestamp DESC", 
            (web_name,)  # Note the comma to make it a tuple
        )
        url = cursor.fetchall()
        
        return {
            # "success": True,
            "url": url,
            # "applications": []  # Keeping this for compatibility
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "urls": [],
            "applications": []
        }
    finally:
        if conn:
            conn.close()



@eel.expose
def get_web_all_info():
    """Get all stored websites from the database"""
    conn = None  # Ensure conn is always defined
    try:
        conn = sqlite3.connect("stored_websites.db")
        cursor = conn.cursor()
        
        # Get all websites
        cursor.execute("SELECT web_name, web_url FROM stored_websites ORDER BY timestamp DESC")
        urls = cursor.fetchall()
        
        return {
            "success": True,
            "url": urls,  # Ensure the key matches the frontend's expectation
            "applications": []  # Keeping this for compatibility
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "url": [],  # Ensure consistency
            "applications": []
        }
    finally:
        if conn:
            conn.close()
    

@eel.expose()
def speak(text):
    """Convert text to speech."""
    engine = pyttsx3.init()
    engine.setProperty("rate", 160)
    engine.say(text)
    engine.runAndWait()


@eel.expose
def get_voice_command(timeout=5):
    """Function to recognize voice input with a timeout."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print('Listening....')
        r.pause_threshold = 2
        r.adjust_for_ambient_noise(source)
        try:
            audio = r.listen(source, timeout=timeout)
            print('Recognizing...')
            query = r.recognize_google(audio, language='en-in')
            print(f"User said: {query}")
            return query.lower()
        except sr.WaitTimeoutError:
            print("No command received. Exiting voice mode...")
            return "stop"
        except Exception:
            return None

@eel.expose
def get_news(query):
    """Fetch precise English headlines using Mediastack."""
    base_url = "http://api.mediastack.com/v1/news"
    params = {
        "access_key": MEDIASTACK_API_KEY,
        "keywords": query,
        "languages": "en",  # Ensure headlines are in English
        "limit": 30000,  # Limit to 5 headlines for precision
        "sort": "published_desc",  # Get the latest news first
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        news_data = response.json()
        
        return news_data
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news data: {e}")
        return None

@eel.expose
def speak_news(query):
    """Speak the precise English headlines for a given query."""
    news_data = get_news(query)
    if news_data and news_data.get("data"):
        eel.speak(f"Here are the top headlines for {query}:")
        for article in news_data["data"]:  # Loop through articles
            title = article["title"]
            eel.displayMessage(title, "response")
            eel.speak(title)
    else:
        speak(f"Sorry, I couldn't fetch the news for {query}.")





@eel.expose
def get_non_assistant_response(user_input):
    """Process user command and return response."""
    response = ""

    if user_input.startswith("weather "):
        city = user_input.replace("weather ", "").strip()
        response = get_weather(city)

    elif user_input.startswith("news"):
        topic = user_input.replace("news", "").strip()
        news_data = get_news(topic)
        if news_data and news_data.get("data"):
            headlines = [article["title"] for article in news_data["data"]]
            response = " | ".join(headlines) if headlines else "No news found."
        else:
            response = "Couldn't fetch news."

    elif user_input.startswith("launch "):
    # Extract the website name
        web_name = user_input.replace("launch ", "").strip()
    
    # Fetch URL from the database
        web_info = get_webinfo(web_name)  # Renamed to web_info for clarity
    
        if web_info and "url" in web_info and web_info["url"]:
        # Get the first URL from the results (fetchall returns a list of tuples)
        # Assuming you want the most recent URL (ordered by timestamp DESC)
            url = web_info["url"][0][0]  # First row, first column
            webbrowser.open(url)  # Open website in default browser
            response = f"Launching {web_name} in your default browser..."
        else:
            response = f"Website '{web_name}' not found in database."
    
    
    elif user_input.startswith("open"):
        app = user_input.split(" ", 1)[-1].strip()
        open_app(app)
        response = f"Opening {app}..."

    elif user_input.startswith("close"):
        app = user_input.split(" ", 1)[-1].strip()
        close_app(app)
        response = f"Closing {app}..."

    elif user_input.startswith("set volume"):
        number = extract_number(user_input.split())
        if number is not None:
            set_volume_percentage(number)
            response = f"Volume set to {number}%"

    elif user_input.startswith("set brightness"):
        number = extract_number(user_input.split())
        if number is not None:
            set_brightness(number)
            response = f"Brightness set to {number}%"

    elif user_input.startswith("create folder"):
        folder = user_input.split(" ", 2)[-1].strip()
        create_folder(folder)
        response = f"Folder '{folder}' created."

    elif user_input.startswith("delete folder"):
        folder = user_input.split(" ", 2)[-1].strip()
        delete_folder(folder)
        response = f"Folder '{folder}' deleted."

    # New search functionality added here
    elif user_input.startswith("search"):
        query = user_input.replace("search", "").strip()
        if query:
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            webbrowser.open(search_url)
            response = f"Searching Google for: {query}"
        else:
            response = "Please specify what to search for."

    else:
        response = "Command not recognized."

    # Send response to frontend immediately
    eel.displayMessage(response, "response")

    # Speak the response after updating the UI
    speak(response)



@eel.expose
def get_assistant_response(user_input):
    if user_input.lower().startswith("hey pluto "):  # Case-insensitive check
        query = user_input.replace("hey pluto ", "").strip()
        assistant = chat_with_deepseek(query)  # Fetch response from DeepSeek

        eel.displayMessage(assistant, "assistant")  # Display in UI

        # Save only DeepSeek queries and responses in the database
        save_to_db(user_input, assistant)

        speak(assistant)  # Convert response to speech
        
        # return assistant  # Return the response

    # If input doesn't start with "hey pluto ", do nothing (no return statement)




@eel.expose
def get_chat_history():

    """Return the chat history from the database to the frontend."""
    return get_chat_history_from_db()


@eel.expose
def clear_chat_history():
    """Deletes all chat history from the database."""
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history")  # Clear all history
    conn.commit()
    conn.close()


def chat_with_deepseek(user_input):
    """Send user input to DeepSeek API and return the response."""
    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-chat-v3.1:free",
           messages=[
        {"role": "system", "content": "Answer in 2-3 concise sentences. Avoid markdown formatting."},
        {"role": "user", "content": user_input}
    ],
            stream=False,
        )
        # Extract the response content
        deepseek_response = response.choices[0].message.content
        return deepseek_response
    except Exception as e:
        return f"Error with DeepSeek: {e}"


@eel.expose
def get_weather(city):
    response1 = requests.get(f"http://api.weatherapi.com/v1/current.json?key={WEATHERAPI_KEY}&q={city}")
    data = response1.json()
    response = f"{city}: {data['current']['temp_c']}°C, {data['current']['condition']['text']}"
    eel.displayMessage(response, "response")
    speak(response)
        
    

def open_app(app_name):
    """Open an application and bring it to the front."""
    try:
        AppOpener.open(app_name)  # Open the app
        time.sleep(2)  # Give it time to launch

        # Get the application window
        windows = gw.getWindowsWithTitle(app_name)
        if windows:
            window = windows[0]
            window.minimize()  # Minimize first
            window.restore()  # Restore to bring it to the front
            return f"{app_name} opened successfully."
        else:
            return f"Opened {app_name}, but couldn't find its window."
    except Exception as e:
        return f"Couldn't open {app_name}: {str(e)}"

def close_app(app_name):
    """Close an application."""
    try:
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if app_name.lower() in process.info["name"].lower():
                os.kill(process.info["pid"], signal.SIGTERM)
                return f"Closed {app_name}"
    except:
        return f"Couldn't close {app_name}"

def set_volume_percentage(percent):
    """Set system volume."""
    volume.SetMasterVolumeLevelScalar(percent / 100, None)

def set_brightness(level):
    """Set screen brightness."""
    wmi.WMI(namespace="wmi").WmiMonitorBrightnessMethods()[0].WmiSetBrightness(level, 0)

def extract_number(words):
    """Extract number from text."""
    for word in words:
        try:
            return w2n.word_to_num(word)
        except:
            continue
    return None

def create_folder(folder_name):
    """Create folder on Desktop."""
    path = os.path.join(os.path.expanduser("~/OneDrive/Desktop"), folder_name)
    os.makedirs(path, exist_ok=True)

def delete_folder(folder_name):
    """Delete folder from Desktop."""
    path = os.path.join(os.path.expanduser("~/OneDrive/Desktop"), folder_name)
    if os.path.exists(path):
        os.rmdir(path)

# Get screen resolution
screen_width, screen_height = pyautogui.size()

# Start Eel
eel.start("index.html", size=(screen_width, screen_height))

