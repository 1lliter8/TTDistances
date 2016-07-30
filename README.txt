                -- Distances Calculation Tool --
                --      by Will Langdale      --
                --           v1.0             --
                --    wpflangdale@gmail.com   --

I am deeply proud to have finally completed my first tool that will 
save someone somewhere some time and effort, despite costing me more 
hours than I'm willing to count in its construction. No matter, it's 
a learning task!

The Distances Calculation Tool is a GUI application created to quickly 
calculate the distances between big sets of TicketTree data. It is 
used to create files that Phil can use to quickly update the TicketTree 
website with the data. The program works with Phil's already-written
TicketTree webservice and Google Maps Distance Matrix API to do its
calculations, and exports a JSON object in .txt format.

                     -- Using the tool --

Ignore distances.py - that's the source code. ui3.ui and intro.ui 
MUST be located in the same directory as distances.exe if you copy or 
move the program.

Click distances.exe. A command prompt window will open followed by 
a prompt for a username and password. Phil protects TicketTree's 
webservice with this information and he can give you what needs to 
be popped in there. Google's Distance Matrix API has something like 
2000 free requests you can make a day, 100 every 10 seconds. While 
the program handles this, I never went over the free limit, and 
if you manage to go over this the program will almost certainly just 
crash and spit nonsense into the command prompt window that opens 
at the start. If we ever pay for Google data, the API key goes in 
the optional third field.

Once you're in, the program will begin getting data from TicketTree, 
with progress shown in the big loading bar at the bottom. Depending on 
your internet connection (this will work from home), the requests 
take between 10 seconds and 4 minutes. This is due to the structure 
of the TicketTree webservice, sorry.

On the right is a dropdown with cities loaded from the site's data, 
so any messiness is from bad TicketTree data. Just type the 
destination name, and its latitude and longitude taken from Google 
Maps, select the journey type and click "get distances". You'll 
get another loading bar which will take about 10 seconds to update, 
and once it's done it'll let you use the "save distances" button 
to save it all.

At the top you can change between working with Hotels or Theatres. 
You can check various hotels and theatres but swapping tab clears 
it down, so you can only check one of the tabs at a time. 
Checking stuff will also make the cities dropdown change to 
"checked items" rather than a particular city. Have a play. Note 
that the city dropdown controls the data you send to Google - 
if you have a load of items checked and the box says "London", 
London hotels is what you'll get from Google.

Do also note that there is NO DATA VALIDATION ON WHAT YOU PUT IN. 
What you put in, regardless of what you do or type, will get sent 
to Google when you click "Get distances". If you don't like it go 
check distances manually like a schmuck rather than hanging out 
with the cool dudes living in the future.

                   -- Updating the tool --

Okay, here's the good stuff - I'll try and be thorough.

The program is written in Python 2.7 and uses suds and PyQt as well 
as a few core libraries. Both are free, but PyQt requires a hefty 
commercial licence if you plan to sell this, so don't. It was 
compiled to exe using pyinstaller and its awesome --onefile 
option which made me want to cry it was so simple. The only 
downside is the terminal that sits in the background looking 
suspicious, and if I had time I'd look into sorting that out. For 
now, too bad!

.ui files are editable in Qt Designer which comes with PyQt, and 
because the program loads these each time it starts, as long as you 
don't change the name of the objects (for example destCity) then 
nothing will blow up. This means if you don't like my aesthetic 
choices you can alter it, even though they were right in the first 
place.

Python is hopefully readable enough that you'll be able to understand 
my code without too much trouble - I try to write a comment for 
every method and class so I know what everything does. Look down the 
bottom for where it all gets going. If __name__ == "__main__" is 
a standard Python thing for running stuff. The classes are:

IntroUI - A QDialog that gets username and password

TTUI - A QWidget that holds the main program and the functions for 
   the buttons. Like most GUIs, Qt has an event loop that listens 
   for "signals" that go into "slots", so the connections made in 
   this class's instantiation do all that stuff

TTDaemon - Not actually a daemon, but was once during the build 
   process. I was unaware of QThreads so I used Python's core 
   threading library, and QObjects can only be updated from the main 
   program thread. To get round this this class emits custom signals 
   to do stuff in TTUI

TTComms - Handles communication with TicketTree. Includes some 
   funky borrowed code (first time I've ever used a decorator) to 
   make threadsafe queues. Suds handles SOAP requests. Populates 
   two dictionaries, tt_prochotels and tt_proctheatres, which 
   hold all the information that in turn populates TTUI's tables. 
   You'll also find some nightmarish stacks of index lookups to 
   get the right data from the TicketTree webservice, and if I did 
   this again the first thing I would do would be to write a new 
   webservice. It takes about 900 requests for the program to get 
   the data it needs. What on earth!

GoogleComs - Some basic nonsense for making URLs to send to Google 
   in the right format. TTUI actually has most of the code that 
   breaks it into 10-second chunks of 100 items.

If you want to know how this all works then my recommendation would 
be:

-Learn Python 2.7 (though 3 would probably be fine). Codeacademy is 
   free. Learn Python The Hard Way is also decent.
-Learn Qt. This is a good intro: http://zetcode.com/gui/pyqt4/
   The uic module was my biggest stumbling block to easy Qt where 
   you import a .ui file then just refer to each element as 
   "self.objectname" without explicitly instatiating them. Have a 
   look at some examples here: 
   http://nullege.com/codes/search/PyQt4.uic.loadUiType

                        -- Licences --

None, free, it's yours. I'd appreciate my name left on it if it 
isn't edited to somehow become deeply offensive. I explicitly 
forbid racist variable names.