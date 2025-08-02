from discord.ext import commands
from discord.ui import Button
from discord.utils import get
from discord import FFmpegPCMAudio
from Token import Token
from subprocess import Popen, PIPE, STDOUT
from Playlist import Playlist
from Search import search
import datetime, discord, os, asyncio

debug = False
CH_ID = 'NONE'
PATH = '/'.join(os.path.abspath(__file__).split("\\")[:-1])
vc = None
curr = None
autoPlay = True
info = []

repeat = 0
skip = True
page = 0

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description='Relatively simple music bot example',
    intents=intents,
)

class PREV_BTN(Button):
    def __init__(self):
        super().__init__(label='◀ 이전 목록', 
                         style=discord.ButtonStyle.green,
                         custom_id=f'{bot.user.id}_PREV_BTN')

class NEXT_BTN(Button):
    def __init__(self):
        super().__init__(label='다음 목록 ▶',
                         style=discord.ButtonStyle.green,
                         custom_id=f'{bot.user.id}_NEXT_BTN')

class CLS_BTN(Button):
    def __init__(self):
        super().__init__(label='창 닫기',
                         style=discord.ButtonStyle.red,
                         custom_id=f'{bot.user.id}_CLS_BTN')

class SEND_INFO_BTN(Button):
    def __init__(self):
        super().__init__(label='DM으로 전송',
                         style=discord.ButtonStyle.primary,
                         custom_id=f'{bot.user.id}_SEND_INFO_BTN')

def DEBUG(line):
    if not debug: return
    print(line)

def TODAY():
    today = datetime.datetime.now()
    date = today.strftime('%Y-%m-%d')
    return date

def TIMENOW():
    today = datetime.datetime.now()
    time = today.strftime('%H:%M:%S')
    return time

def get_name(user):
    name = user.nick
    if name == None:
        name = str(user.name)
    return name

def PRINT_CTX(ctx):
    today = TODAY()
    timenow = TIMENOW()
    author = get_name(ctx.author)
    print(f'\n[{today} {timenow}] {author} / {ctx.message.content}')

def IS_MINE(ctx):
    global CH_ID

    if CH_ID == 'NONE': return True
    elif str(ctx.channel.id) == CH_ID: return True
    else:
        print(f"NOT MY CHANNEL, PASS THE COMMAND / CH : {ctx.channel.name}")
        return False
    

def CAN_USE(ctx, commandType=''):
    try: ch = ctx.message.author.voice.channel
    except: return "채널에 참여한 후에 사용해주세요!"

    bot_channel = get(ctx.bot.voice_clients, guild=ctx.guild)
    if bot_channel == None: return True
    
    if str(bot_channel.channel) != str(ch):
        return "이미 다른 채널에서 사용중입니다!\n같은 채널에 참여한 후에 사용해주세요!"
    
    if commandType == 'control':
        try:
            if not vc.is_playing(): return "노래가 재생중이지 않습니다!\n노래를 재생한 후에 사용해주세요!"
        except:
            return f"{bot.user.name}(이)가 작동 중이지 않습니다!\n{bot.user.name}(이)가 작동 중일 때, "\
                    "다시 사용해주세요!"

    return True
    
def play_next():
    global skip, repeat, curr, autoPlay

    if skip:
        skip = False
        res, curr = Playlist.popSong(autoPlay)
        if not res: return

    elif repeat == 0:
        res, curr = Playlist.popSong(autoPlay)
        if not res: return

    elif repeat == 2:
        Playlist.pushSong(curr)
        res, curr = Playlist.popSong()
    
    vc.play(FFmpegPCMAudio(curr['url'], **ffmpeg_options), after=lambda e: play_next())
    if 'spotifyID' in curr.keys(): Searcher.addAutoQueue([curr['spotifyID'], curr['title']])
    else: Searcher.addAutoQueue([None, curr['title']])
    Playlist.appendAutoQueue()
    
async def JOIN_CHANNEL(ctx):
    global vc
    
    try: vc = await ctx.message.author.voice.channel.connect()
    except Exception as e: print(e)

    return True

def playMusic():
    global vc, curr, autoPlay
    if vc is None or not vc.is_playing():
        res, curr = Playlist.popSong()
        vc.play(FFmpegPCMAudio(curr['url'], **ffmpeg_options), after=lambda e: play_next())
    if autoPlay and len(Playlist.getList(False)[1])==0: Searcher.addAutoQueue([None, curr['title']])
    return

@bot.command(aliases=['PLAY', 'Play', 'ㅔㅣ묘', 'ㅖㅣ묘', 'p', 'P', 'ㅔ', 'ㅖ',
                      '재생', '째생', '쨰생', 'wotod', 'WOTOD', 'Wotod', 'WOtod',
                      'o', 'O', 'ㅐ', 'ㅒ', '[', '{'])
async def play(ctx):
    global vc, repeat, skip, curr, p, autoPlay, info
    if IS_MINE(ctx) == False: return
    res = CAN_USE(ctx)
    if res != True:
        embed = discord.Embed(title="오류 발생", description = res, color=0xff0000)
        await ctx.reply(embed=embed)
        return
    PRINT_CTX(ctx)

    embed = discord.Embed(title="노래 검색 중...", 
                          description = f"{get_name(ctx.author)} 님의 신청곡을 검색중입니다.\n잠시만 기다려주세요!")
    info = await ctx.reply(embed=embed)
    msg = ' '.join(ctx.message.content.split(' ')[1:])
    title, hyperlink, ID = Searcher.getURL(msg)
    Searcher.addPlayQueue([ID, msg])

    if vc is None:
        await JOIN_CHANNEL(ctx)
        autoPlay = True
    if curr is None:
        curr = title
        await info.edit(embed = discord.Embed(title= "노래 재생", 
                        description = "현재 '" + title + "' 을(를) 재생합니다.\n"\
                                      f"[동영상 바로가기]({hyperlink})",
                        color = 0x00ff00))
    else:
        await info.edit(embed = discord.Embed(title = "대기열 등록",
                        description = f"'{title}' 을(를) 대기열에 추가할게요!\n"\
                                      f"[동영상 바로가기]({hyperlink})",))
    Searcher.addAutoQueue(['RESET', None])
    return

@bot.command(aliases=['qksqhr', 'loop', 'l', 'ㅣㅐㅐㅔ', 'repeat', 'r', 'ㄱ덷ㅁㅅ', '앵콜', 'dodzhf', '도르마무', 'ehfmakan', 'ㅂㅂ', 'qq'])
async def 반복(ctx):
    global repeat
    if IS_MINE(ctx) == False: return
    res = CAN_USE(ctx, 'control')
    if res != True:
        embed = discord.Embed(title="오류 발생", description = res, color=0xff0000)
        await ctx.reply(embed=embed)
        return
    PRINT_CTX(ctx)
    
    if repeat == 0:
        repeat = 1
        await ctx.reply(embed = discord.Embed(title = "한 곡 반복", description = "현재 재생중인 노래를 반복합니다."))
    elif repeat == 1:
        repeat = 2
        await ctx.reply(embed = discord.Embed(title = "재생목록 반복", description = "현재 재생목록을 반복합니다."))
    else:
        repeat = 0
        await ctx.reply(embed = discord.Embed(title = "반복없음", description = "반복재생을 해제합니다."))

@bot.command(aliases=['나ㅑㅔ', '넘기기', 'sjarlrl', 'sk', '나', '다음', 'ekdma', '스킵', 'tmzlq', '스킾', 'tmzlv', 'ㅅㅋ', 'tz', 'ㄴㄱㄱ', 'srr'])
async def skip(ctx):
    global skip
    if IS_MINE(ctx) == False: return
    res = CAN_USE(ctx, 'control')
    if res != True:
        embed = discord.Embed(title="오류 발생", description = res, color=0xff0000)
        await ctx.reply(embed=embed)
        return
    PRINT_CTX(ctx)
    
    if vc.is_playing():
        skip = True
        vc.stop()
        await ctx.reply(embed = discord.Embed(title= "Skip",
                                        description = "'" + curr['title']  + "' 을(를) 종료했습니다.",
                                        color = 0xff0000))
    else:
        await ctx.reply("지금 노래가 재생되지 않네요.")

@bot.command(aliases=['tkrwp', '삭제', 'ㄱ드ㅐㅍㄷ', 'delete', 'ㅇ딛ㅅㄷ', 'ㅅㅈ', 'tw', '취소', 'ㅊㅅ'])
async def remove(ctx):
    if IS_MINE(ctx) == False: return
    res = CAN_USE(ctx, 'control')
    if res != True:
        embed = discord.Embed(title="오류 발생", description = res, color=0xff0000)
        await ctx.reply(embed=embed)
        return
    PRINT_CTX(ctx)

    msg = ctx.message.content.split(' ')
    num1 = 1
    num2 = 2
    if len(msg)>1: num1 = msg[1]
    if len(msg)>2: num2 = msg[2]

    if '번' in num1: num1 = num1.replace('번', '')
    if ',' in num1: num1, num2 = map(int, num1.split(','))
    num1 = int(num1)
    num2 = int(num2)

    res, tmp = Playlist.delSong(num1, num2)

    if tmp[0]+1 == tmp[1]: tmp = f'{tmp[0]}번'
    else: tmp = f'{tmp[0]}번 ~ {tmp[1]}번'

    embed = discord.Embed(title = "재생목록 삭제",
                          description = f"재생목록 {tmp} 노래를 삭제했습니다.",
                          color = 0xff0000)
    
    await ctx.reply(embed = embed)

@bot.command(aliases=['나가', '끄기', 'whdfy', 'Rmrl', 'stop', 'ㄴ새ㅔ', '중단', '사라져', '중지', 'ㅈㄹ', 'wf', 'ㅈㄷ', 'we', 'ㅈㅈ', 'ww', '꺼져', '꺼저'])
async def 종료(ctx):
    global time, vc
    if IS_MINE(ctx) == False: return
    res = CAN_USE(ctx, 'control')
    if res != True:
        embed = discord.Embed(title="오류 발생", description = res, color=0xff0000)
        await ctx.reply(embed=embed)
        return
    PRINT_CTX(ctx)

    name = bot.user.name
    await vc.disconnect()
    vc = None
    await ctx.reply(embed = discord.Embed(title = "노래 멈춰!", 
                                    description = f"{name}가 콘서트를 종료합니다.", 
                                    color = 0xff0000))

@bot.command(aliases=['목록셔플', '노ㅕㄹ릳', '셔플', 'tuvmf', 'ahrfhrtuvmf', '쇼플', 'tyvmf'])
async def shuffle(ctx):
    if IS_MINE(ctx) == False: return
    res = CAN_USE(ctx, 'control')
    if res != True:
        embed = discord.Embed(title="오류 발생", description = res, color=0xff0000)
        await ctx.reply(embed=embed)
        return
    PRINT_CTX(ctx)
    
    res, tmp = Playlist.shuffle()
    if not res:
        await ctx.reply(embed = discord.Embed(title = "오류 발생",
                                          description = tmp,
                                          color = 0xff0000))
    else:
        await ctx.reply(embed = discord.Embed(title = "재생목록 셔플",
                                          description = "성공적으로 셔플되었습니다.",
                                          color = 0x00ff00))

@bot.command(aliases=['wlrmashfo', '무슨노래', 'antmsshfo', 'nowplay', 'ㅜㅐ제ㅣ묘', 'np', 'ㅞ', '지금재생', 'wwlrmawotod', 'ㅈㄱㄴㄹ', 'wrsf', '뭐냐'])
async def 지금노래(ctx):
    if IS_MINE(ctx) == False: return
    PRINT_CTX(ctx)
    
    try:
        if not vc.is_playing():
            await ctx.reply(embed = discord.Embed(title = "오류 발생", description = "지금은 노래가 재생되고 있지 않습니다!", color = 0xff0000))
            return
    except:
        await ctx.reply(embed = discord.Embed(title = "오류 발생", description = f"{bot.user.name}(이)가 작동 중이지 않습니다!\n{bot.user.name}(이)가 작동 중일 때, 다시 사용해주세요!", color = 0xff0000))
        return
        
    embed = discord.Embed(title = "지금 듣고 계신 곡은 ?",
                          description = f"**{curr['title']}**\n재생시간 [{curr['duration']}]"\
                            f"\n[동영상 바로가기](https://www.youtube.com/watch?v={curr['ID']})",
                          color = 0x00ff00)
    
    view = discord.ui.View()
    view.add_item(SEND_INFO_BTN())
    view.add_item(CLS_BTN())
    await ctx.reply(embed = embed, view=view)

@bot.command(aliases=['wwewt','autoplay','ㅈㄷㅈㅅ', 'auto', 'wkehdwotod'])
async def 자동재생(ctx):
    global autoPlay
    if IS_MINE(ctx) == False: return
    res = CAN_USE(ctx, 'control')
    if res != True:
        embed = discord.Embed(title="오류 발생", description = res, color=0xff0000)
        await ctx.reply(embed=embed)
        return
    PRINT_CTX(ctx)

    autoPlay = not autoPlay
    if autoPlay: embed = discord.Embed(title='자동재생', description='자동재생을 시작합니다.')
    else: embed = discord.Embed(title='자동재생', description='자동재생을 종료합니다.')
    await ctx.reply(embed=embed)

def makeQueueEmbed(num=0):
    global autoPlay
    res, queue = Playlist.getList(autoPlay)

    q = len(queue)//10 + 1
    num %= q

    if repeat==0: rpt='반복없음'
    elif repeat==1: rpt='한 곡 반복'
    elif repeat==2: rpt='재생목록 반복'

    embed = discord.Embed(title = f"♬ {curr['title']}",
                          description = f'재생목록 | 반복재생 : {rpt} | 자동재생사용 : {autoPlay}',
                          color = 0xf3bb76)

    if not res: return embed

    for i in range(num*10, min(len(queue),(num+1)*10)):
        if 'spotifyID' in queue[i].keys():
            embed.add_field(name=f"{i+1}. {queue[i]['title']}",
                        value=f"자동재생 / 재생시간 [{queue[i]['duration']}]",
                        inline=False)
        else:
            if 'https://' in queue[i]['msg']:
                embed.add_field(name=f"{i+1}. {queue[i]['title']}",
                        value=f"검색어 : {queue[i]['ID']} | 재생시간 [{queue[i]['duration']}]"\
                            f" | [바로가기](https://www.youtube.com/watch?v={queue[i]['ID']})",
                        inline=False)
            else:
                embed.add_field(name=f"{i+1}. {queue[i]['title']}",
                        value=f"검색어 : {queue[i]['msg']} | 재생시간 [{queue[i]['duration']}]"\
                            f" | [바로가기](https://www.youtube.com/watch?v={queue[i]['ID']})",
                        inline=False)
    return embed

@bot.command(aliases=['재생목록', '목록', 'list', 'queue', 'q', 'Queue', '벼뎓', 'eorlduf', 'ㄷㄱㅇ', 'erd'])
async def 대기열(ctx):
    global page
    if IS_MINE(ctx) == False: return
    PRINT_CTX(ctx)
    
    try:
        if not vc.is_playing():
            await ctx.reply(embed = discord.Embed(title = "오류 발생",
                                            description = "현재 재생중인 노래가 없습니다.",
                                            color = 0xff0000))
            return
    except:
        await ctx.reply(embed = discord.Embed(title = "오류 발생", 
                                        description = f"{bot.user.name}(이)가 작동 중이지 않습니다!",
                                        color = 0xff0000))
        return

    view = discord.ui.View()
    view.add_item(PREV_BTN())
    view.add_item(NEXT_BTN())
    view.add_item(CLS_BTN())
    
    await ctx.reply(embed = makeQueueEmbed(), view = view)

@bot.command(aliases=['query', 'ai', 'AI'])
async def 검색(ctx):
    if IS_MINE(ctx) == False: return
    PRINT_CTX(ctx)
    
    msg = ' '.join(ctx.message.content.split(' ')[1:])
    embed = discord.Embed(title=f'{msg}', description ="AI 검색 결과 생성 중...")
    info = await ctx.reply(embed=embed)

    res = Searcher.useGemini(msg)
    embed = discord.Embed(title=f"{msg}", description = f"{res}")
    await info.edit(embed=embed)

@bot.event
async def on_interaction(interaction):
    global page, rpt
    
    msg = interaction.message
    ID = interaction.data['custom_id']

    if str(bot.user.id) in ID:
        try:
            await interaction.response.defer()
        except:
            pass
    else:
        return

    if ID == f'{bot.user.id}_PREV_BTN':
        page-=1

        view = discord.ui.View()
        view.add_item(PREV_BTN())
        view.add_item(NEXT_BTN())
        view.add_item(CLS_BTN())
    
        await msg.edit(embed = makeQueueEmbed(page), view = view)
        
    elif ID == f'{bot.user.id}_NEXT_BTN':
        page+=1

        view = discord.ui.View()
        view.add_item(PREV_BTN())
        view.add_item(NEXT_BTN())
        view.add_item(CLS_BTN())
    
        await msg.edit(embed = makeQueueEmbed(page), view = view)
        
    elif ID == f'{bot.user.id}_CLS_BTN':
        await msg.delete()

    elif ID == f'{bot.user.id}_SEND_INFO_BTN':
        des = msg.embeds[0].description
        start = des.find("**")
        end = des.rfind("**")
        embed = discord.Embed(title = "DM으로 음악 정보 전송", description = "요청하신 곡은\n**" + des[start+2:end] + "**\n입니다.", color = 0x00ff00)
        await interaction.user.send(embed=embed)
        
@bot.event
async def on_ready():
    global CH_ID
    print(f'{bot.user} (ID: {bot.user.id})')
    print('성공적으로 연결되었습니다.')
    await bot.change_presence(status=discord.Status.online, activity=None)

    try:
        Path = f'{PATH}/CH_ID.txt'
        with open(Path, 'r', encoding='utf-8') as f:
            lin = f.read()
        CH_ID = lin.replace('\n','')
        print(f'명령어 채널 설정됨 / CH_ID : {CH_ID}')
    except:
        pass

@bot.event
async def on_voice_state_update(member, before, after):
    global vc, repeat
    
    if not member.id == bot.user.id:
        return

    elif before.channel is None:
        timenow = TIMENOW()
        print(f'\n{bot.user.name} is CONNECTED to {after.channel} AT {timenow}')
        time = 0
        while True:
            await asyncio.sleep(10)
            time += 10
            if time > 55: await vc.disconnect()
            if vc is None: break
            elif vc.is_playing() or vc.is_paused(): time = 0
            if not vc.is_connected():
                await asyncio.sleep(1)
                if not vc.is_connected():
                    vc=None
                    print(f'\n{bot.user.name} is DISCONNECTED from {after.channel} '\
                          f'AT {TIMENOW()} / variale time = {time}')
                    break

@bot.event
async def on_command_error(ctx, error):
    print(error)
    ctx.message.content = ctx.message.content.replace('!', '!p ')
    await play(ctx)

Playlist = Playlist()
Searcher = search(Playlist, playMusic)
bot.run(Token)