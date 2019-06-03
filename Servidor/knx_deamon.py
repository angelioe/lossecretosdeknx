import asyncio, getopt, sys, sqlite3, datetime, threading, time

from xknx import XKNX
from xknx.io import GatewayScanner, Tunnel
from xknx.knx import DPTBinary, GroupAddress, PhysicalAddress, Telegram, AddressFilter


async def telegram_received_cb(telegram):
    connt = sqlite3.connect('./FlaskApp/hopeitworks.db')
    telegram_str=str(telegram)
    date_time=str(datetime.datetime.now())+" "+str(datetime.datetime.today().weekday())
    group_address,DPT,value,telegram_type,direction=split_telegram(telegram_str)
    c = connt.cursor()
    c.execute("SELECT VALUE FROM DATA WHERE CONTROLLER=? AND DEVICE=? AND FUNCTION=? ORDER BY ID DESC LIMIT 1",("knx",group_address,DPT))
    all_rows = c.fetchall()
    if (str(all_rows) != "[]"):
        if (str(all_rows)[3:-4]!=value):
            print(telegram_str)
            c.execute("INSERT INTO DATA (DATE_TIME,CONTROLLER,DEVICE,FUNCTION,VALUE)\
                            VALUES (?,?,?,?,?)",[date_time,"knx",group_address,DPT,value]);
    else:
        c.execute("INSERT INTO DATA (DATE_TIME,CONTROLLER,DEVICE,FUNCTION,VALUE)\
                        VALUES (?,?,?,?,?)",[date_time,"knx",group_address,DPT,value]);
    connt.commit()
    connt.close()
    return True

def split_telegram(telegram):
    telegram_str=str(telegram)
    garbage,telegram_rest=telegram_str.split('GroupAddress("',1)
    group_address,telegram_rest=telegram_rest.split('"',1)
    garbage,telegram_rest=telegram_rest.split('payload="<',1)
    DPT,telegram_rest=telegram_rest.split('value="',1)
    value,telegram_rest=telegram_rest.split('" />" telegramtype="',1)
    telegram_type,telegram_rest=telegram_rest.split('" direction="',1)
    direction,telegram_rest=telegram_rest.split('" />',1)
    return(group_address,DPT,value,telegram_type,direction)

def split_telegram_ins(telegram):
    telegram_str=str(telegram)
    id,device,function,value = telegram_str.split(",")
    id = id[2:len(id)]
    device = device[2:-1]
    function = function[2:-1]
    value = value[2:-3]
    return(id,device,function,value)


async def monitor(address_filters,db):
    xknx = XKNX()
    xknx.telegram_queue.register_telegram_received_cb(telegram_received_cb, address_filters)
    await xknx.start()
    await xknx.telegram_queue.process_telegram_outgoing(Telegram(GroupAddress('0/0/1'), payload=DPTBinary(1)))
    while True:
        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute('SELECT {id},{coi1},{coi2},{coi3} FROM {tn} WHERE {cn}="knx" AND {cs}="p" ORDER BY {ord} DESC LIMIT 1'.\
        format(id='ID',coi1='DEVICE', coi2='FUNCTION', coi3='VALUE', tn='INSTRUCTIONS', cn='CONTROLLER', cs='STATE', ord='ID'))
        all_rows = c.fetchall()
        if (str(all_rows) != "[]"):
            id,device,function,value = split_telegram_ins(all_rows)
            if (function == "bin"):
                await xknx.telegram_queue.process_telegram_outgoing(Telegram(GroupAddress(device), payload=DPTBinary(int(value))))
                c.execute('UPDATE {tn} SET {cs}="d" WHERE {ide}=id'.\
                format(tn='INSTRUCTIONS', cs='STATE', ide='ID'))
                date_time=str(datetime.datetime.now())+" "+str(datetime.datetime.today().weekday())
                c.execute("SELECT VALUE FROM DATA WHERE CONTROLLER=? AND DEVICE=? AND FUNCTION=? ORDER BY ID DESC LIMIT 1",("knx",device,function))
                all_rows = c.fetchall()
                if (str(all_rows) != "[]"):
                    if (str(all_rows)[3:-4]!=value):
                        conn.execute("INSERT INTO DATA (DATE_TIME,CONTROLLER,DEVICE,FUNCTION,VALUE)\
                                        VALUES (?,?,?,?,?)",[date_time,"knx",device,function,value]);
                else:
                    conn.execute("INSERT INTO DATA (DATE_TIME,CONTROLLER,DEVICE,FUNCTION,VALUE)\
                                    VALUES (?,?,?,?,?)",[date_time,"knx",device,function,value]);
                conn.commit()

        conn.close()
        await asyncio.sleep(0.1)
    await xknx.stop()



if __name__ == "__main__":

    conn = sqlite3.connect('./FlaskApp/hopeitworks.db')
    db = './FlaskApp/hopeitworks.db'
    try:
        conn.execute('''CREATE TABLE INSTRUCTIONS
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                 DATE_TIME TEXT NOT NULL,
                 CONTROLLER TEXT NOT NULL,
                 DEVICE TEXT NOT NULL,
                 FUNCTION TEXT NOT NULL,
                 VALUE TEXT NOT NULL,
                 STATE TEXT NOT NULL);''')
        conn.execute('''CREATE TABLE DATA
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                 DATE_TIME TEXT NOT NULL,
                 CONTROLLER TEXT NOT NULL,
                 DEVICE TEXT NOT NULL,
                 FUNCTION TEXT NOT NULL,
                 VALUE TEXT NOT NULL);''')
    except:
        e = "Database already created"

    conn.close()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(monitor(None,db))
    loop.close()
