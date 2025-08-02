from random import shuffle, randint
from Search import search

class Playlist:
    def __init__(self):
        self.curr = None
        self.Queue = []
        self.AutoPlayQueue = []
        self.AutoPlayPool = []
        self.AutoPlaySet = set()
        self.Seacher = search()

    def __del__(self):
        del self.Queue
        del self.AutoPlayQueue

    def pushSong(self, song):
        self.Queue.append(song)
        return [True, '']
    
    def popSong(self, Autoplay=True):
        if len(self.Queue)==0:
            if Autoplay:
                song = self.AutoPlayQueue[0]
                del self.AutoPlayQueue[0]
            else: return [False, "대기열이 비어있습니다."]
        else:
            song = self.Queue[0]
            del self.Queue[0]
        self.curr = song
        return [True, song]
    
    def delSong(self, start=1, end=2):
        swap = False
        if len(self.Queue)==0:
            self.Queue = self.AutoPlayQueue
            swap = True
        if start<1: start=1
        if end>len(self.Queue): end=len(self.Queue)
        if end<=start: end=start+1
        for _ in range(end - start): del self.Queue[start-1]
        if swap:
            self.AutoPlayQueue = self.Queue
            self.Queue = []
        return [True, [start, end]]
    
    def addAutoPool(self, song):
        if song['spotifyID'] in self.AutoPlaySet: return
        self.AutoPlaySet.add(song['spotifyID'])
        self.AutoPlayPool.append(song)
        self.appendAutoQueue()

    def appendAutoQueue(self):
        if len(self.AutoPlayPool)==0: return
        if len(self.AutoPlayQueue)<10:
            idx = randint(0, len(self.AutoPlayPool)-1)
            sel = self.AutoPlayPool.pop(idx)
            song = self.Seacher.getMusic([sel['ID'], sel['msg']])
            song['spotifyID'] = sel['spotifyID']
            self.AutoPlayQueue.append(song)
            del sel
        return

    def shuffle(self):
        if len(self.Queue + self.AutoPlayQueue)==0: return [False, "대기열이 비어있습니다."]
        shuffle(self.Queue)
        shuffle(self.AutoPlayQueue)
        return [True, '']

    def reset(self):
        del self.Queue
        del self.AutoPlayQueue
        del self.AutoPlayPool
        del self.AutoPlaySet
        self.Queue = []
        self.AutoPlayQueue = []
        self.AutoPlayPool = []
        self.AutoPlaySet = set()
        return [True, '']

    def resetAutoplay(self):
        del self.AutoPlayQueue
        del self.AutoPlayPool
        del self.AutoPlaySet
        self.AutoPlayQueue = []
        self.AutoPlayPool = []
        self.AutoPlaySet = set()
        return [True, '']

    def getFront(self, Autoplay=True):
        if len(self.Queue)==0:
            if Autoplay: return [True, self.AutoPlayQueue[0]]
            else: return [False, "대기열이 비어있습니다."]
        else: return [True, self.Queue[0]]

    def getBack(self, Autoplay=True):
        if len(self.Queue)==0:
            if Autoplay: return [True, self.AutoPlayQueue[-1]]
            else: return [True, self.curr]
        else: return [True, self.Queue[-1]]

    def getList(self, Autoplay=True):
        if Autoplay: return [True, self.Queue + self.AutoPlayQueue]
        else: return [True, self.Queue]
