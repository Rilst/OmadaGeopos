from omada import Omada
from aiohttp import web
import asyncio, datetime, redis, threading, aiosqlite, json


authed = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
currentpos = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)

omada = Omada('omada.cfg')
omada.login()

async def CreateDatabase():
    async with aiosqlite.connect('Statistic.db') as db:
        await db.execute('pragma journal_mode=wal')
        await db.execute('CREATE TABLE IF NOT EXISTS Statistic '
                         '(Date timestamp NOT NULL, ApMac text NOT NULL, Count integer DEFAULT 0, id integer PRIMARY KEY AUTOINCREMENT)')
        await db.commit()

def handle(request):
    authed.set(request.rel_url.query['mac'], request.rel_url.query['phone'], ex=28800)
    return True

loop = asyncio.get_event_loop()
app = web.Application()
app.add_routes([web.get('/', handle)])
handler = app.make_handler()
server = loop.create_server(handler, host='127.0.0.1', port=45452)
def aiohttp_server():
    loop.run_until_complete(server)
    loop.run_forever()
t = threading.Thread(target=aiohttp_server)
t.start()


async def getPos():
    await CreateDatabase()
    while True:
        for client in omada.getSiteClients():
            if client.get('mac') != None and client.get('authStatus') == 2:
                if currentpos.get(client['mac']) != client['apMac']:
                    async with aiosqlite.connect('Statistic.db') as db:
                        id = await db.execute_fetchall('SELECT id FROM Statistic WHERE Date = ? AND ApMac = ?', (datetime.date.today(), client['apMac']))
                        await db.commit()
                        if len(id) != 0:
                            count = await db.execute_fetchall('SELECT Count FROM Statistic WHERE id = ?', (id[0][0],))
                        else:
                            count = []
                        await db.commit()
                        if len(count) != 0:
                            await db.execute('UPDATE Statistic SET Count = ? WHERE id = ? '
                                ,(count[0][0]+1, id[0][0]))
                        else:
                            await db.execute('INSERT INTO Statistic (Date, ApMac, Count)'
                                'VALUES (?,?,?)', (datetime.date.today(), client['apMac'], 1))
                        await db.commit()
                        count = await db.execute_fetchall('SELECT Count FROM Statistic WHERE Date = ? AND ApMac = ?', (datetime.date.today(), "D8-0D-17-68-BF-48"))
                        await db.commit()
                    currentpos.publish("ChangePos", json.dumps({authed.get(client['mac']): client['apMac']}))
                currentpos.set(client['mac'], client['apMac'], ex=60)
        await asyncio.sleep(15)

asyncio.run(getPos())
