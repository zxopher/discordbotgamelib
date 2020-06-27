import discord
from discord.ext import commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from urllib.request import urlopen as uReq
import asyncio
import ast
from bs4 import BeautifulSoup as soup

#things to get setup with google, being authorized and whatnot
scope = [
    "https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]

#credentials in list
creds = ServiceAccountCredentials.from_json_keyfile_name("reputation_creds.json", scope)

#passes in all credentials to make sure changes/ viewing are allowed
sheets_client = gspread.authorize(creds)

# Open the spreadhseet
wb = sheets_client.open('discord_bot_data')

#discord bot token needed to run bot
TOKEN = 'NTY3ODYxODM2MTAwMjcyMTI4.XLZ4Dw.tP4m4pQXGUy9EBDssa2JwLyiM2Y'

#creating client instance and identifying prefix for commands 
prefix = '>>'
discord_client = commands.Bot(command_prefix=prefix)
#discord_client.case_insensitive = True
#removing default help command
discord_client.remove_command('help')

class Game:
    def __init__(self, Data : list):
        self.Owner = str(Data[0])
        self.FullName = str(Data[1])
        self.HoursPlayed = str(Data[2])
        self.SteamID = str(Data[3])
        self.StorePage = str(Data[4])
        self.Multiplayer = str(Data[5])
        self.Downloaded = str(Data[6])
        self.Nickname = str(Data[7])

    def Format_Details(self, formatting):
        Possible_formats = ['f','n','a','h','s','o','d']
        formatted_details = ''
        if 'n' in formatting:
            name_type = self.Nickname
        else:
            name_type = self.FullName

        for char in formatting[1::]:
            if char in Possible_formats:
                if char == 'a':
                    formatted_details += 'Hours: '+self.HoursPlayed+'\n'+'Steam store link: '+self.StorePage+'\n'+'Online: '+self.Multiplayer+'\n'+'Downloaded: '+self.Downloaded
                else:
                    if char == 'h':
                        formatted_details += 'Hours: ' + self.HoursPlayed
                        formatted_details += '\n'
                    if char == 's':
                        formatted_details += 'Steam store link: ' + self.StorePage
                        formatted_details += '\n'
                    if char == 'o':
                        formatted_details += 'Online: ' + self.Multiplayer
                        formatted_details += '\n'
                    if char == 'd':
                        formatted_details += 'Downloaded: ' + self.Downloaded
                        formatted_details += '\n'
                Possible_formats.remove(char)
        return name_type, formatted_details

#Setting the help command to be what the bot is playing 
@discord_client.event
async def on_ready():
    print('Ready set let\'s go')
    await discord_client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=prefix + "help"))

@discord_client.command()
async def update_lib(ctx):
    
    member_name = ctx.author.mention
    # opens sheet that contains info for steam library access
    wks = wb.get_worksheet(1)

    #gets all members names
    usernames_list = wks.col_values(1)

    # runs if memeber has steam info inputted
    if member_name in usernames_list:
        #url to scrap as a varible
        steam_lib_link = wks.cell(usernames_list.index(member_name)+1,4,'FORMATTED_VALUE').value
        
        #opens connection to client website and downloads information
        uClient = uReq(steam_lib_link)

        #mloads html content into variable
        page_html = uClient.read()
        #closes connection to client website
        uClient.close()

        #parse the html document, making soup object
        page_soup = soup(page_html, "html.parser")

        #getting all game containers list
        json_script = page_soup.find_all("script",{"language":"javascript"})

        #editting data as a string to be convertable to a dictionary
        all_game_info = json_script[0].next.split(';')[0]
        all_game_info = all_game_info[len("  			var rgGames = ["):-1]
        all_game_info = all_game_info.replace("},{", "},,{")
        all_game_info = all_game_info.replace('\\','')
        all_game_info = all_game_info.replace('false','False')
        all_game_info = all_game_info.replace('true','True')
        undicted_game_info = list(all_game_info.split(",,"))
        #sets game info sheet to active
        wks = wb.get_worksheet(0)
        
        #gets the current sheet to be compared to tell if new games needed to be added
        current_sheet = wks.get_all_values()
        for game in undicted_game_info:
            game_info_dict = ast.literal_eval(game)
            if 'hours_forever' in game_info_dict:
                useful_game_info = [member_name, game_info_dict['name'], game_info_dict['hours_forever'], game_info_dict['appid'], 'https://store.steampowered.com/app/'+str(game_info_dict['appid']), 'TBD', 'no', 'none',]

            #find out if game is multiplayer and or other tags
            #add tags to spreadsheet
            #loops through each row in the games sheet to update and add new games to sheet
            row_count = 1
            
            for row in current_sheet:
                if row[:2] == useful_game_info[:2]:
                    wks.update_cell(row_count, 3, useful_game_info[2])
                row_count+=1
            for row in current_sheet:
                del row[2:]
                row = list(set(row))
            if not useful_game_info[:2] in current_sheet:
                wks.append_row(useful_game_info,'RAW')
        await ctx.send("```Your library has been updated```")
    else:
        await ctx.send("```I do not have a Steam ID for you, please go create one with the 'steamID' command```")

@discord_client.command()
async def download(ctx, GameIndex):
    pass

@discord_client.command()
async def steamID(ctx, input_id):
    member_name = ctx.author.mention
    #await ctx.send(member_name)
    wks = wb.get_worksheet(1) #open second sheet

    usernames_list = wks.col_values(1)
    #await ctx.send(usernames_list)

    if member_name in usernames_list:
        username_row = usernames_list.index(member_name) + 1
        wks.update_cell(username_row, 2, input_id)
        await ctx.send('```Your information has been updated```')

    else:
        new_user_info = [member_name,input_id, "https://steamcommunity.com/profiles/"+input_id, "https://steamcommunity.com/profiles/" + input_id + "/games/?tab=all"]
        wks.append_row(new_user_info, 'RAW')
        await ctx.send('```New infomation added```')
                
@discord_client.command()
async def help(ctx, commandName=None):

    if commandName == None:
        helpEmbed = discord.Embed(title = 'List of short command descriptions', color = discord.Color.orange())
        helpEmbed.add_field(name = 'Command Prefix: ', value =  'put this, "' + prefix + '", in front of specified command name to be able to call the command', inline=False)
        helpEmbed.add_field(name = 'help', value = 'One optional arguement: commandName\nSpecify a command\'s name to get more details on that command', inline=False)
        helpEmbed.add_field(name = 'echo', value = 'Repeats what you say in a fancy code block', inline=False)
        helpEmbed.add_field(name = 'readLib', value = 'Allows you and others to read the games you have installed.', inline=False)
        helpEmbed.add_field(name = 'delItem', value = 'Deletes specified item from library', inline=False)
        helpEmbed.add_field(name = 'steamID', value = 'Either creates new profile for member or updates exsisting Steam ID number', inline=False)


    elif commandName == 'echo':
        helpEmbed = discord.Embed(title = 'In depth help for ', color = discord.Color.orange())
        helpEmbed.add_field(name = commandName, value = 'Repeats what you say in a fancy code block\n\nOne optional arguement: message\n\nIf the arguement is not filled then the message defaults to \'echo\'\n\nThe arguement can be as long as you want including spaces\n\n Default Example: >>echo\nDefault Ouptut: echo\n\nFilled Argument Example: >>echo This command is useless \nFilled arguement Output: This command is useless')

    elif commandName == 'addItem':
        helpEmbed = discord.Embed(title = 'In depth help for ', color = discord.Color.orange())
        helpEmbed.add_field(name = commandName, value = 'Adds a game to your library for you and others to look at\n\nFour needed arguements: Game\'s name, Game\'s nickname, Launcher, and whether you can play with friends or not(yes or no)\n\nUse dashes where you want spaces in names, these will turn into spaces in your libray. However use spaces for distinguishing arguements\n\nExample: >>addItem The-Elder-Scrolls-V:-Skyrim Skyrim Steam Yes \nOuptut: Successfully added')

    elif commandName == 'readLib':
        helpEmbed = discord.Embed(title = 'In depth help for ', color = discord.Color.orange())
        helpEmbed.add_field(name = commandName, value = 'Allows you and others to read the games you have installed.\n\nThis command has one manditory command: username and one optional command: formatting\nSpecify your username or another person\'s in the server to read the users library of games\nThe formatting command allows your to read more or less details of the library of the user you specify. To do this you must put a \'-\' then put any number of and combination of the letters \'f\' \'n\' \'l\' \'o\'.\n\'f\': will make the full game\'s name part of the bot\'s output of the library.\n\'n\': will make the game\'s nickname part of the bot\'s output of the library.\n')

    await ctx.send(embed=helpEmbed)

@discord_client.command() 
async def echo(ctx, *, msg='echo'):
    await ctx.send(f"""```{msg}```""")
    await ctx.send("```changes work```")
    
@discord_client.command()
async def readLib(ctx, user_mention, formatting=None):
    library_embeds = []
    wks = wb.get_worksheet(0) #open first sheet
    current_sheet = wks.get_all_values()
    num_of_games = len(wks.findall(user_mention))
    user_mention = user_mention.replace('!', '')
    LibraryEmbed = discord.Embed(title = user_mention + "'s library", description = "Maximum of 5 games per page." , color = discord.Color.orange())
    embeded_game_count = 0
    #checks what kind of formatting the memeber would like; all options include "-fnlo"; any combination may be used e.g. "-oln"
    if formatting == None:
        for row in current_sheet:
            if not row == current_sheet[0]:
                item = Game(row)
                if item.Owner == user_mention:
                    embeded_game_count += 1
                    LibraryEmbed.add_field(name=item.FullName, value='Downloaded: ' + item.Downloaded, inline=False)
                    if embeded_game_count%5 == 0 or num_of_games - embeded_game_count == 0:
                        library_embeds.append(LibraryEmbed)
                        LibraryEmbed = discord.Embed(title = user_mention + "'s library", description = "Maximum of 5 games per page." , color = discord.Color.orange())
        await ctx.send(embed=library_embeds[0]) #len(library_embeds)-1])
    
    elif formatting[0] == '-':
        validQuery = True
        
        for char in formatting[1::]:
            if not char in ['f','n','a','h','s','o','d']:
                await ctx.send(f"""```Format type unknown+{repr(char)}```""")
                validQuery = False

        if validQuery == True:            
            for row in current_sheet:
                if not row == current_sheet[0]:
                    item = Game(row)
                    if item.Owner == user_mention:
                        game_details = item.Format_Details(formatting)
                        embeded_game_count += 1
                        LibraryEmbed.add_field(name=game_details[0], value=game_details[1], inline=False)
                        if embeded_game_count%5 == 0 or num_of_games - embeded_game_count == 0:
                            library_embeds.append(LibraryEmbed)
                            LibraryEmbed = discord.Embed(title = user_mention + "'s library", description = "Maximum of 5 games per page." , color = discord.Color.orange())
            await ctx.send(embed=library_embeds[0])
    
#discord_client.loop.create_task(update_libs())
discord_client.run(TOKEN)