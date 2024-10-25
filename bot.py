import discord
from discord.ext import commands
import sqlite3
import config

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Bot()
bot = commands.Bot(command_prefix='!', intents=intents) #bot command prefix
conn = sqlite3.connect('botDB.db') #sqlite DB
yes = "✅"
no =  "❌"
role = "" #role id to @ tag in message can be blank

msglist = ""
attendances = {}

@bot.event
async def on_ready(): #on bot fully started
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_guild_join(guild): #on server join check if bot has been there if not make an entry in the DB
    cur = conn.cursor()
    res = cur.exectue("SELECT serverid FROM attendance WHERE serverid = ?",(guild.id,))
    if res.fetchone() is None:
        print(f"been here before {guild.name}")
    else:
        cur.execute("INSERT INTO attendance VALUES ?, NULL, NULL, NULL, NULL, NULL",(guild.id,))
        conn.commit()
        
@bot.command() 
async def reactchan(ctx): #user set reaction channel
    cur = conn.cursor()
    await ctx.send("react channel set")
    cur.execute("UPDATE attendance SET reactChannelid = ? WHERE serverid = ?",(str(ctx.channel.id),str(ctx.guild.id)))
    conn.commit()

@bot.command()
async def reportchan(ctx):  #user set report channel
    cur = conn.cursor()
    await ctx.send("report channel set")
    cur.execute("UPDATE attendance SET reportChannelid = ? WHERE serverid = ?",(str(ctx.channel.id),str(ctx.guild.id)))
    conn.commit()

@bot.command()
async def attendance(ctx): #main command
    cur = conn.cursor()
    res = cur.execute("SELECT reactChannelid,reportChannelid FROM attendance WHERE serverid= ?",(str(ctx.guild.id),)).fetchone()
    if res[1] == "": #catch if channels not setup
        await ctx.send("please set a react message channel with !reactchan and a report channel with !reportchan   if you don't do both the report channel will be the same channel as the react channel")
        pass
    if ctx.channel.id == res[0]:
#send messge.
        if role != "":
            msgrole = f"<@&{role}>"
        else:
            msgrole = ""
        msg = await ctx.send(f"Are you showing up to this next event? {msgrole}")

        await msg.add_reaction(yes)
        await msg.add_reaction(no)
#get list of users in the channel message was sent in 
        chan = bot.get_channel(msg.channel.id)
        members = chan.members #finds members connected to the channel
        memids = {} 
        temp = ""
        for member in members:
            if member.bot == False:
                memids[member.name] = "[N/A]❓"
        for x, y in memids.items():
            temp = temp + f"{x} -- {y}\n"
#handel report channel message
        if res[1] == "": #catch for if only the react channel is setup so it will user the react channel over the report channel
            reportchan = bot.get_channel(res[0])
        else:
            reportchan = bot.get_channel(res[1])
        reactmsg = await reportchan.send(f"people attending:\n\n{temp}")
#put all in DB
        cur.execute("UPDATE attendance SET ReactMSGid = ?, reportMSGid = ?, MSG = ? WHERE serverid = ?",(str(msg.id),str(reactmsg.id),str(temp),str(ctx.guild.id)))
        conn.commit()


@bot.event
async def on_reaction_add(reaction, user): #on user reacts to bots message
    cur = conn.cursor()
    message = reaction.message
    res = cur.execute("SELECT reactChannelid, reportChannelid, reactMSGid, reportMSGid, MSG FROM attendance WHERE serverid= ?",(str(message.guild.id),)).fetchone()
    if message.id == res[2]: #bot message id
        if message.author == bot.user:#### #doesn't need to be there as its by message id 
            if user != bot.user: #make sure its a user react and not bots first time.
#break up message content into something easier to edit aka a dict
                message = res[4] #get message connect from DB
                message = message.split("\n")
                for i in range(len(message)-1):
                    temp = message[i].split(" -- ") 
                    attendances[temp[0]] = temp[1] #yay we finally have the dict to update fml
                if str(reaction) == yes: #checking the emoji
                    attendances[user.name] = f"[attending]{yes}"
                if str(reaction) == no: #checking the emoji
                    attendances[user.name] = f"[not attending]{no}"
                temp = ""
                for x, y in attendances.items():
                    temp = temp + "{} -- {}\n".format(x,y)
#update bot message
                cur.execute("UPDATE attendance SET MSG = ? WHERE serverid = ?",(str(temp),str(reaction.message.guild.id)))
                conn.commit()
#edit the report message
                message = bot.get_message(res[3])
                await message.edit(f"people attending:\n\n{temp}")

bot.run(config.token)
