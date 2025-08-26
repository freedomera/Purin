import yt_dlp, requests, queue, threading, bs4, time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import spotipy
from to_Spotify import CID, SECRET
from to_Gemini import Gemini_Key
from spotipy.oauth2 import SpotifyClientCredentials
import google.generativeai as genai

class search:
    def __init__(self, Playlists=None, playMusic=None):

        yt_dlp.utils.bug_reports_message = lambda: ''
        
        ytdl_format_options = {
            'format': 'bestaudio/best',
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
        }
        self.ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

        if Playlists is None or playMusic is None: return

        self.PlayQueue = queue.Queue()
        self.PlayThread = threading.Thread(target=self.processPlayQueue)
        self.PlayThread.start()

        self.AutoQueue = queue.Queue()
        self.AutoplayThread = threading.Thread(target=self.processAutoplayQueue)
        self.AutoplayThread.start()

        self.Playlists = Playlists
        self.playMusic = playMusic

        options = Options()
        options.add_argument('headless')
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--remote-allow-origins=*")
        options.add_argument("--disable-features=WidevineCdm")
        options.add_argument("--user-data-dir=D:\chromedriver-win64\Default")
        self.driver = webdriver.Chrome(options=options)
        
        cid = CID
        secret = SECRET
        client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)
        self.sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

        genai.configure(api_key=Gemini_Key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def useGemini(self, req):
        response = self.model.generate_content(req).text
        return response
    
    def addPlayQueue(self, req):
        self.PlayQueue.put(req)

    def processPlayQueue(self):
        while True:
            req = self.PlayQueue.get()
            print("Process Play Queue :",req,'\n')
            self.addMusic(req)
    
    def addAutoQueue(self, req):
        self.AutoQueue.put(req)

    def processAutoplayQueue(self):
        while True:
            req = self.AutoQueue.get()
            print("Process Autoplay Queue :",req,'\n')
            if req[0]=='RESET':
                self.Playlists.resetAutoplay()
                continue
            try: self.searchAutoplayList(req)
            except Exception as e: print(e,'\n')
            
    def stop(self):
        self.PlayThread.join()
        self.AutoplayThread.join()

    def timeTstr(self, Time):
        hours = int(Time/3600)
        Time -= 3600*hours
        minutes = int(Time/60)
        Time -= 60*minutes
        secs = Time
        
        if hours >= 1:
            Time = '{:02d}:{:02d}:{:02d}'.format(hours, minutes, secs)
        else:
            Time = '{:02d}:{:02d}'.format(minutes, secs)
            
        return Time

    def getURL(self, msg):
        mozhdr = {'User-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36"}
        if 'https://www.youtube.com/watch?v=' in msg:
            url = msg
            idx = msg.find('watch?v=') + len('watch?v=')
            ID = msg[idx:idx+11]
            html = requests.get(url, headers=mozhdr).text
            start = int(html.find('<title>'))+len('<title>')
            html = html[start:]
            end = int(html.find(' - YouTube</title>'))
            title = html[:end]
            del idx, html, start, end
            
        elif 'https://youtu.be/' in msg:
            url = msg
            idx = msg.find('https://youtu.be/') + len('https://youtu.be/')
            ID = msg[idx:idx+11]
            html = requests.get(url, headers=mozhdr).text
            start = int(html.find('<title>'))+len('<title>')
            html = html[start:]
            end = int(html.find(' - YouTube</title>'))
            title = html[:end]
            del idx, html, start, end
            
        else:
            keyword = msg.replace(' ','+').replace('#', '')
            url = "https://www.youtube.com/results?search_query="+keyword+'+lyrics'
            html = requests.get(url, headers=mozhdr).text
            start = int(html.find('"webCommandMetadata":{"url":"/watch?v='))
            ID = html[start+38:start+49]
            url = 'https://www.youtube.com/watch?v='+ID
            start = int(html.find('"title":{"runs":[{"text":"'))+len('"title":{"runs":[{"text":"')
            html = html[start:]
            end = int(html.find('"}],"'))
            title = html[:end]
            del keyword, mozhdr, html, start, end
        
        return title, url, ID

    def getMusic(self, DATA):
        ID, msg = DATA[0], DATA[1]
        data = self.ytdl.extract_info('https://www.youtube.com/watch?v='+ID, download=False)
        song = dict()
        song['title'] = data['title']
        song['ID'] = ID
        song['duration'] = self.timeTstr(data['duration'])
        song['url'] = data['url']
        song['msg'] = msg
        return song

    def addMusic(self, DATA):
        self.Playlists.pushSong(self.getMusic(DATA))
        if self.playMusic: self.playMusic()

    def searchAutoplayList(self, DATA):
        if len(self.Playlists.AutoPlayPool)>30: return
        ID, title = DATA[0], DATA[1]
        if ID is None:
            response = self.model.generate_content(f"'{title}'가 커버 곡이라면 원곡의 '제목'만 출력하고"\
                "아니라면 '가수 제목'을 출력해줘").text.replace('\n','')
            print(f"{response} found about {title}")
            res = self.sp.search(response, limit=1, type='track')
            ID = res['tracks']['items'][0]['id']
        print("Preparing Auto Playlist for ID :", ID)
        self.driver.get('https://open.spotify.com/track/'+ID)
        #print("Wait for Page")
        time.sleep(5)
        #print("Page Loading Complete")
        del ID
        html = bs4.BeautifulSoup(self.driver.page_source, 'html.parser')
        html = html.find('div', {'class':"oIeuP60w1eYpFaXESRSg"})
        ele = html.find_all('div', {'class':"_iQpvk1c9OgRAc8KRTlH"})
        del html
        #print("html parsing complete")
        for E in ele:
            trackID = E.find('a',{'class':"GIyB7JDkRwjtVL6PSBbg"})['href'][7:]
            res = self.sp.track(trackID)
            artist = res['artists'][0]['name']
            title = res['name']
            print("Music Found :", artist, title)
            tit, url, ID = self.getURL(f"{artist} {title}")
            print(f"Youtube Result : {tit} ({ID})\n")
            song = dict()
            song['ID']=ID
            song['msg']=f"{artist} {title}"
            song['spotifyID']=trackID
            self.Playlists.addAutoPool(song)
            del song
