from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip

import os
import random

_: Translator = Translator("MafiaGame", __file__)


def get_image(image_name: str) -> discord.File:
    file = discord.File(
        os.path.join(os.path.dirname(__file__), "images", f"{image_name}.png"),
        filename=f"{image_name.split(os.path.sep)[-1]}.png",
    )
    file._closer = file.reset
    return file


def get_death_reason(member: discord.Member) -> str:
    return random.choice(
        [
            _("The Mafia killed {member.display_name} because they were too good at video games."),
            _("The Mafia killed {member.display_name} because they were too sus."),
            _(
                "{member.display_name} thought hiding in a bush would work... turns out, Mafia members love gardening."
            ),
            _(
                "{member.display_name} tried to convince the Mafia that they were one of them. The cement shoes were not convinced."
            ),
            _("{member.display_name} slept with one eye open... but forgot about the second one."),
            _(
                "{member.display_name} thought they were safe in witness protection... until they accidentally posted their location on social media."
            ),
            _(
                "{member.display_name} went to bed early, but the Mafia came knocking. They were just dying to meet them."
            ),
            _(
                "{member.display_name} tried to bribe the Mafia with Monopoly money. It didn't go over well."
            ),
            _(
                '{member.display_name} tried to blend in with the crowd. Unfortunately, they were holding a sign that said "Not Mafia".'
            ),
            _(
                "{member.display_name} tripped over a body while sneaking around. Unfortunately, it was their own."
            ),
            _(
                "{member.display_name} thought they had outsmarted the Mafia. The Mafia let them think that... for about 5 seconds."
            ),
            _(
                "{member.display_name} tried to fake their own death, but the Mafia decided to make it official."
            ),
            _(
                "{member.display_name} had a foolproof plan to expose the Mafia... until they realized they were the fool."
            ),
            _(
                "{member.display_name} thought the Mafia meeting was a potluck. They brought the wrong dish... and didn't live to fix it."
            ),
            _(
                "{member.display_name} asked the Mafia if they were hiring. They handed over a job offer... permanently."
            ),
            _(
                "{member.display_name} was caught monologuing about how they knew the Mafia's secret. The Mafia loves a dramatic pause."
            ),
            _(
                "{member.display_name} tried to hide behind the curtains, but forgot that the Mafia doesn't do theater."
            ),
            _(
                "{member.display_name} thought the Mafia wouldn't attack on a Tuesday. The Mafia loves a surprise."
            ),
            _(
                "{member.display_name} was last seen trying to explain the concept of 'trust' to the Mafia. It didn't go well."
            ),
            _(
                "{member.display_name} attempted to outvote the Mafia, but the votes were already counted... in bullets."
            ),
            _(
                "{member.display_name} tried to reason with the Mafia but forgot they don't negotiate with amateurs."
            ),
            _(
                "{member.display_name} thought they could blend in by wearing a mustache. The Mafia prefers clean shaves."
            ),
            _("{member.display_name} brought a knife to a Mafia gunfight. It didn't end well."),
            _(
                "{member.display_name} thought they were safe in witness protection, until they ordered pizza... from the wrong family."
            ),
            _(
                "{member.display_name} challenged the Mafia to a game of chess. The Mafia preferred Russian roulette."
            ),
            _(
                "{member.display_name} thought they could expose the Mafia at the town meeting. The Mafia was already running it."
            ),
            _(
                "{member.display_name} tried to hide in plain sight, but forgot the Mafia has excellent vision at night."
            ),
            _(
                "{member.display_name} attempted to bribe the Mafia with cookies. The Mafia prefers cold, hard cash."
            ),
            _(
                "{member.display_name} tried to outsmart the Mafia but forgot they don't play by the rules."
            ),
            _(
                "{member.display_name} thought the Mafia would spare them if they complimented their suits. They were wrong."
            ),
            _("{member.display_name} tried to run, but the Mafia always gets their steps in."),
            _("{member.display_name} went fishing, but it turns out the Mafia owns the lake."),
            _(
                "{member.display_name} tried to play dead, but the Mafia knows how to check for a pulse."
            ),
            _(
                "{member.display_name} thought switching towns would work, but the Mafia had a welcome party waiting."
            ),
            _(
                "{member.display_name} attempted to turn the Mafia against each other... and ended up turning into a ghost instead."
            ),
            _(
                "{member.display_name} thought they could outwit the Mafia, but ended up outwitting themselves."
            ),
            _(
                "{member.display_name} tried to frame someone else, but the Mafia is good at framing... and finishing."
            ),
            _(
                "{member.display_name} thought leaving town would save them, but the Mafia has long arms."
            ),
            _(
                "{member.display_name} tried to hide in a bakery. The Mafia loves their bread... and revenge."
            ),
            _(
                "{member.display_name} was writing a tell-all book about the Mafia. Unfortunately, the final chapter was... short."
            ),
            _(
                "{member.display_name} thought they could sneak out, but the Mafia always hears everything."
            ),
            _("{member.display_name} tried to out-dodge the Mafia, but bullets travel faster."),
            _(
                "{member.display_name} thought joining a rival gang would protect them. The Mafia had other plans."
            ),
            _(
                "{member.display_name} hid in the back of a getaway car... unfortunately, it was the Mafia's."
            ),
            _(
                "{member.display_name} thought they were clever, but the Mafia is always two steps ahead."
            ),
            _(
                "{member.display_name} tried to play innocent, but the Mafia doesn't believe in fairy tales."
            ),
            _(
                "{member.display_name} thought hiding in a crowd would work, but the Mafia knew exactly who to look for."
            ),
            _("{member.display_name} tried to flee on a boat, but the Mafia controls the docks."),
            _(
                "{member.display_name} tried to expose the Mafia in the newspaper. They forgot who owns the printing press."
            ),
            _(
                "{member.display_name} attempted to bribe the Mafia with favors. The Mafia prefers cash—lots of it."
            ),
            _(
                "{member.display_name} thought they could hide behind a lawyer, but the Mafia hired a better one."
            ),
            _("{member.display_name} tried to disappear, but the Mafia has eyes everywhere."),
            _(
                "{member.display_name} thought pretending to be asleep would save them. The Mafia never sleeps."
            ),
            _(
                "{member.display_name} tried to fake their own death. The Mafia kindly made it real."
            ),
            _(
                "{member.display_name} thought they could negotiate with the Mafia. The only deal they got was a one-way ticket."
            ),
            _("{member.display_name} tried to hide in the shadows, but the Mafia owns the night."),
            _(
                "{member.display_name} thought wearing a disguise would help. The Mafia recognized them by their shoes."
            ),
            _(
                "{member.display_name} tried to dig up dirt on the Mafia. They ended up six feet under."
            ),
            _(
                "{member.display_name} thought they could trust a stranger. Turns out, the stranger worked for the Mafia."
            ),
            _(
                "{member.display_name} tried to send an anonymous tip. The Mafia intercepted the message."
            ),
            _(
                "{member.display_name} thought hiding in the church would work. Even the priest couldn't save them from the Mafia."
            ),
            _(
                "{member.display_name} tried to escape by train. The Mafia was already waiting at the station."
            ),
            _(
                "{member.display_name} thought the Mafia wouldn't strike in broad daylight. They were mistaken."
            ),
            _(
                "{member.display_name} tried to throw the Mafia off their trail, but they don't lose track of loose ends."
            ),
            _(
                "{member.display_name} thought hiding in the sewers was clever. The Mafia’s already been down there."
            ),
            _(
                "{member.display_name} tried to outdrink the Mafia. They didn’t survive the hangover."
            ),
            _(
                "{member.display_name} thought they'd blend in at a costume party. The Mafia always knows who’s under the mask."
            ),
            _(
                "{member.display_name} tried to take the back alley shortcut, but the Mafia controls all the exits."
            ),
            _(
                "{member.display_name} thought the Mafia wouldn’t notice their getaway car. It was rigged before they even got in."
            ),
            _(
                "{member.display_name} tried to hide behind the bar, but the Mafia owns the whole building."
            ),
            _(
                "{member.display_name} thought they could use a fake name. The Mafia has real bullets."
            ),
            _(
                "{member.display_name} tried to hide in the freezer, but the Mafia prefers things on ice."
            ),
            _(
                "{member.display_name} thought going underground would keep them safe. The Mafia digs deeper."
            ),
            _(
                "{member.display_name} tried to sneak past the Mafia, but they were waiting on the other side."
            ),
            _(
                "{member.display_name} thought they could bribe their way out. The Mafia doesn't take credit cards."
            ),
            _("{member.display_name} tried to run for mayor, but the Mafia runs the whole town."),
            # ...
            _(
                "{member.display_name} thought they could make a getaway on a jet ski. The Mafia prefers concrete boots."
            ),
            _(
                "{member.display_name} tried to play a double agent, but the Mafia only trusts in triples."
            ),
            _(
                "{member.display_name} thought they could blend in by becoming a street performer. The Mafia doesn’t tip well."
            ),
            _(
                "{member.display_name} tried to escape through the sewer pipes, but the Mafia had already sealed the exits."
            ),
            _(
                "{member.display_name} thought bribing the doorman would help. The Mafia owns the whole building."
            ),
            _(
                "{member.display_name} tried to hide in a crowd at a festival. The Mafia knows how to find the needle in the haystack."
            ),
            _(
                "{member.display_name} tried to use a fake ID. The Mafia’s database is always up to date."
            ),
            _(
                "{member.display_name} thought joining the local poker game would keep them safe. The Mafia always knows when you’re bluffing."
            ),
            _(
                "{member.display_name} tried to disappear into the nightlife, but the Mafia controls all the nightclubs."
            ),
            _(
                "{member.display_name} tried to use their charm to get out of trouble. The Mafia prefers a different kind of persuasion."
            ),
            _(
                "{member.display_name} thought they were safe at home. The Mafia knows no boundaries."
            ),
            _(
                "{member.display_name} tried to escape on a hot air balloon. The Mafia prefers a more grounded approach."
            ),
            _(
                "{member.display_name} thought faking a sickness would save them. The Mafia doesn’t fall for medical excuses."
            ),
            _(
                "{member.display_name} tried to blend in at the local gym. The Mafia doesn’t exercise; they execute."
            ),
            _(
                "{member.display_name} thought they could hide in the library. The Mafia reads all the chapters, including the last one."
            ),
            _(
                "{member.display_name} tried to blend in at the masquerade ball. The Mafia always knows who’s behind the mask."
            ),
            _(
                "{member.display_name} thought they could evade the Mafia by taking a scenic route. They enjoyed the view... one last time."
            ),
            _(
                "{member.display_name} attempted to hide in a dumpster. The Mafia knows all the best hiding spots."
            ),
            _(
                "{member.display_name} thought they could escape by plane. The Mafia controls the airport."
            ),
            _(
                "{member.display_name} tried to bribe their way out with counterfeit money. The Mafia doesn’t deal in fakes."
            ),
            _(
                "{member.display_name} thought a new identity would protect them. The Mafia has an extensive directory."
            ),
            _(
                "{member.display_name} tried to flee during a blackout. The Mafia doesn’t need lights to find their targets."
            ),
            _(
                "{member.display_name} thought joining a cult would offer protection. The Mafia prefers their own brand of loyalty."
            ),
            _(
                "{member.display_name} tried to sneak into a VIP party. The Mafia owns the guest list."
            ),
            _(
                "{member.display_name} thought they could escape in a hot air balloon. The Mafia’s reach extends even skyward."
            ),
            _(
                "{member.display_name} tried to hide in the attic. The Mafia has eyes on every floor."
            ),
            _(
                "{member.display_name} thought a disguise would save them. The Mafia recognizes all the tricks."
            ),
            _(
                "{member.display_name} tried to hide in the shadows. The Mafia knows how to turn on the spotlight."
            ),
            _(
                "{member.display_name} attempted to bribe a police officer. The Mafia owns the precinct."
            ),
            _(
                "{member.display_name} thought escaping through a secret passage would work. The Mafia has a map of every route."
            ),
            _(
                "{member.display_name} tried to hide in a church. The Mafia doesn’t believe in sanctuary."
            ),
            _(
                "{member.display_name} thought they could lose the Mafia by switching vehicles. The Mafia tracks all their cars."
            ),
            _("{member.display_name} tried to escape via yacht. The Mafia controls the docks."),
            _(
                "{member.display_name} thought leaving town would be enough. The Mafia has connections everywhere."
            ),
            _(
                "{member.display_name} attempted to blend in at a costume shop. The Mafia always sees through the disguise."
            ),
            _(
                "{member.display_name} tried to use their knowledge of the city to hide. The Mafia knows the city better."
            ),
            _(
                "{member.display_name} thought changing their appearance would help. The Mafia recognizes more than just faces."
            ),
            _(
                "{member.display_name} tried to use a fake accent. The Mafia can spot a phony from a mile away."
            ),
            _(
                "{member.display_name} thought hiding in plain sight at a parade would be safe. The Mafia doesn’t miss a beat."
            ),
            _(
                "{member.display_name} tried to blend in at a sporting event. The Mafia has tickets to all games."
            ),
            _(
                "{member.display_name} thought a new haircut would disguise them. The Mafia notices even the smallest changes."
            ),
            _(
                "{member.display_name} tried to sneak out during a street festival. The Mafia controls all the festivities."
            ),
            _(
                "{member.display_name} thought they could outsmart the Mafia with a fake alibi. The Mafia prefers real evidence."
            ),
            _(
                "{member.display_name} tried to hide in a crowded market. The Mafia always finds the needle in the haystack."
            ),
            _(
                "{member.display_name} attempted to escape in a hearse. The Mafia has no respect for the dead."
            ),
            _(
                "{member.display_name} thought they could evade the Mafia by moving to a rural area. The Mafia’s network is vast."
            ),
            _(
                "{member.display_name} tried to use a decoy. The Mafia sees through all distractions."
            ),
            _(
                "{member.display_name} thought changing their name would protect them. The Mafia has a file on everyone."
            ),
            _(
                "{member.display_name} tried to escape through the sewers. The Mafia knows every underground route."
            ),
            _(
                "{member.display_name} thought moving to a new city would help. The Mafia has operatives everywhere."
            ),
            _(
                "{member.display_name} tried to fake their death at a hospital. The Mafia doesn’t fall for medical tricks."
            ),
            _(
                "{member.display_name} attempted to escape during a power outage. The Mafia is prepared for all contingencies."
            ),
            _(
                "{member.display_name} thought they could hide in a warehouse. The Mafia has access to every storage unit."
            ),
            _(
                "{member.display_name} tried to hide in a film studio. The Mafia knows how to direct their own drama."
            ),
            _(
                "{member.display_name} attempted to leave town by freight train. The Mafia controls all transportation."
            ),
            _(
                "{member.display_name} thought they could escape through a university. The Mafia has connections in every field."
            ),
            _(
                "{member.display_name} tried to lay low at a country club. The Mafia’s reach extends to all social circles."
            ),
            _(
                "{member.display_name} thought they could avoid the Mafia by blending in at a charity event. The Mafia controls all donations."
            ),
            _(
                "{member.display_name} tried to hide in a circus tent. The Mafia doesn’t get fooled by acrobatics."
            ),
            _(
                "{member.display_name} thought a new vehicle would help them escape. The Mafia tracks all types of transportation."
            ),
            _(
                "{member.display_name} tried to blend in at a carnival. The Mafia knows all the games and tricks."
            ),
            _(
                "{member.display_name} attempted to escape via helicopter. The Mafia has helicopters of their own."
            ),
            _(
                "{member.display_name} thought a disguise would save them. The Mafia can see through the most elaborate ruses."
            ),
            _(
                "{member.display_name} tried to avoid the Mafia by moving underground. The Mafia has connections in the sewers."
            ),
            _(
                "{member.display_name} thought a remote cabin would offer safety. The Mafia can find you anywhere."
            ),
            _(
                "{member.display_name} tried to avoid detection by switching neighborhoods. The Mafia owns real estate everywhere."
            ),
            _(
                "{member.display_name} thought they could blend in at a rave. The Mafia controls the nightlife."
            ),
            _(
                "{member.display_name} tried to escape on a bicycle. The Mafia prefers more reliable forms of transport."
            ),
            _(
                "{member.display_name} attempted to hide at a ski resort. The Mafia tracks every snowflake."
            ),
            _(
                "{member.display_name} thought they could escape by becoming a recluse. The Mafia knows every hiding place."
            ),
            _(
                "{member.display_name} tried to use a body double. The Mafia can spot a fake from a mile away."
            ),
            _(
                "{member.display_name} thought joining a commune would protect them. The Mafia infiltrates all communities."
            ),
            _(
                "{member.display_name} tried to hide in a botanical garden. The Mafia has eyes on every petal."
            ),
            _(
                "{member.display_name} thought they could escape by relocating to a remote island. The Mafia’s reach is global."
            ),
            _(
                "{member.display_name} tried to escape through the city's sewer system. The Mafia has access to all underground routes."
            ),
            _(
                "{member.display_name} thought they could evade the Mafia by blending in at a local fair. The Mafia owns the ringmaster."
            ),
            _(
                "{member.display_name} tried to use a distraction to get away. The Mafia always keeps their eyes on the prize."
            ),
            _(
                "{member.display_name} attempted to escape through a network of tunnels. The Mafia knows every exit."
            ),
            _(
                "{member.display_name} thought a secluded farmhouse would keep them safe. The Mafia’s reach extends to the countryside."
            ),
            _(
                "{member.display_name} tried to blend in at a costume party. The Mafia can see through the most elaborate disguises."
            ),
            _(
                "{member.display_name} attempted to flee during a city-wide event. The Mafia controls all major gatherings."
            ),
            _(
                "{member.display_name} thought they could use a false identity. The Mafia has real eyes everywhere."
            ),
            _(
                "{member.display_name} tried to escape via a private jet. The Mafia owns the skies as well."
            ),
            _(
                "{member.display_name} attempted to disappear at a music festival. The Mafia can find you in a crowd."
            ),
            _(
                "{member.display_name} thought they could avoid the Mafia by switching hotels. The Mafia has a booking for every room."
            ),
            _(
                "{member.display_name} tried to escape through a maze. The Mafia knows every twist and turn."
            ),
            _(
                "{member.display_name} thought relocating to a mountain lodge would help. The Mafia controls every peak and valley."
            ),
            _(
                "{member.display_name} tried to escape by blending in at a local art gallery. The Mafia sees all the hidden messages."
            ),
            _(
                "{member.display_name} thought they could hide in a theater during a show. The Mafia controls all the seats."
            ),
            _(
                "{member.display_name} attempted to escape during a sports game. The Mafia has tickets to every match."
            ),
            _(
                "{member.display_name} tried to disappear at a film set. The Mafia is the true star of the show."
            ),
            _(
                "{member.display_name} thought they could hide in an amusement park. The Mafia controls all the rides."
            ),
            _(
                "{member.display_name} tried to escape through a labyrinthine library. The Mafia has read all the books."
            ),
            _(
                "{member.display_name} thought they could use a fake passport. The Mafia has access to all documents."
            ),
            _(
                "{member.display_name} attempted to hide in a fancy restaurant. The Mafia controls all the dining rooms."
            ),
            _(
                "{member.display_name} thought relocating to a small town would help. The Mafia’s network extends even there."
            ),
            _(
                "{member.display_name} tried to use a fake emergency. The Mafia knows when you’re bluffing."
            ),
            _(
                "{member.display_name} thought they could escape through a network of safe houses. The Mafia has maps to all of them."
            ),
            _(
                "{member.display_name} attempted to flee during a blackout. The Mafia sees in the dark."
            ),
            _(
                "{member.display_name} tried to use a body double. The Mafia knows every face in town."
            ),
            _(
                "{member.display_name} thought they could avoid the Mafia by moving to a remote village. The Mafia has connections everywhere."
            ),
            _(
                "{member.display_name} tried to blend in at a local theater production. The Mafia knows all the lines."
            ),
            _(
                "{member.display_name} attempted to escape via a glider. The Mafia has aerial surveillance."
            ),
            _(
                "{member.display_name} thought a new address would help. The Mafia follows all the moving trucks."
            ),
            _(
                "{member.display_name} tried to hide at a local aquarium. The Mafia has eyes on every tank."
            ),
            _(
                "{member.display_name} attempted to disappear at a flea market. The Mafia knows every stall."
            ),
            _(
                "{member.display_name} thought they could blend in at a wine tasting. The Mafia doesn’t miss a drop."
            ),
            _(
                "{member.display_name} tried to escape on a moped. The Mafia prefers more permanent solutions."
            ),
            _(
                "{member.display_name} attempted to hide in a sprawling estate. The Mafia has access to every room."
            ),
            _(
                "{member.display_name} thought a fake medical emergency would buy them time. The Mafia doesn’t fall for stunts."
            ),
            _(
                "{member.display_name} tried to escape through an underground fight club. The Mafia controls all the rings."
            ),
            _(
                "{member.display_name} thought relocating to a desert would save them. The Mafia has a way of finding you even in the sand."
            ),
            _(
                "{member.display_name} tried to hide in a hedge maze. The Mafia has already mapped it out."
            ),
            _(
                "{member.display_name} attempted to escape via a speedboat. The Mafia controls all the docks and marinas."
            ),
            _(
                "{member.display_name} thought a new vehicle would help them flee. The Mafia tracks every license plate."
            ),
            _(
                "{member.display_name} tried to disappear in a crowded train station. The Mafia has agents on every platform."
            ),
            _(
                "{member.display_name} attempted to hide in a high-rise apartment. The Mafia owns the building."
            ),
            _(
                "{member.display_name} thought changing their phone number would help. The Mafia has every number on speed dial."
            ),
            _(
                "{member.display_name} tried to escape by blending in at a local street market. The Mafia owns all the stalls."
            ),
            _(
                "{member.display_name} thought they could hide in a tech convention. The Mafia is always ahead of the latest trends."
            ),
            _(
                "{member.display_name} tried to blend in at a beach resort. The Mafia has a way of finding everyone, even on vacation."
            ),
            _(
                "{member.display_name} attempted to escape through a cable car. The Mafia can track all aerial routes."
            ),
            _(
                "{member.display_name} thought joining a new social club would keep them safe. The Mafia has infiltrated all clubs."
            ),
            _(
                "{member.display_name} tried to hide in a remote logging camp. The Mafia has connections everywhere, even in the woods."
            ),
            _(
                "{member.display_name} thought they could avoid the Mafia by hiding in a rooftop garden. The Mafia always finds a way up."
            ),
            _(
                "{member.display_name} tried to escape through a local brewery. The Mafia has access to all brewing equipment."
            ),
            _(
                "{member.display_name} attempted to blend in at a summer camp. The Mafia has scouts everywhere."
            ),
            _(
                "{member.display_name} thought relocating to a ski lodge would save them. The Mafia tracks all seasonal spots."
            ),
            _(
                "{member.display_name} tried to disappear into the local library’s archive. The Mafia has access to every record."
            ),
            _(
                "{member.display_name} attempted to flee via a private yacht. The Mafia controls every body of water."
            ),
            _(
                "{member.display_name} thought they could avoid detection by blending in at a local flea market. The Mafia knows every vendor."
            ),
            _(
                "{member.display_name} tried to escape through a vintage car club. The Mafia has agents in all classic circles."
            ),
            _(
                "{member.display_name} attempted to hide in an abandoned factory. The Mafia always knows where the abandoned places are."
            ),
            _(
                "{member.display_name} thought changing their appearance with surgery would help. The Mafia recognizes even the smallest changes."
            ),
            _(
                "{member.display_name} tried to escape by hopping a freight train. The Mafia tracks all shipments."
            ),
            _(
                "{member.display_name} attempted to hide in a local historic site. The Mafia has a history of finding their targets."
            ),
            _(
                "{member.display_name} thought they could blend in at a comedy club. The Mafia has no sense of humor about betrayal."
            ),
            _(
                "{member.display_name} tried to avoid the Mafia by living off the grid. The Mafia finds ways to turn off-grid back on."
            ),
            _(
                "{member.display_name} attempted to escape via a mountain pass. The Mafia knows all the treacherous routes."
            ),
            _(
                "{member.display_name} thought they could hide in a boutique hotel. The Mafia has connections in every corner of hospitality."
            ),
            _(
                "{member.display_name} tried to disappear at a magic show. The Mafia prefers their own brand of illusions."
            ),
            _(
                "{member.display_name} attempted to hide in a scientific research lab. The Mafia has spies everywhere, even in labs."
            ),
            _(
                "{member.display_name} thought relocating to a coastal town would help. The Mafia has eyes on every coast."
            ),
            _(
                "{member.display_name} tried to escape during a charity gala. The Mafia controls all the high society."
            ),
            _(
                "{member.display_name} attempted to disappear in a spa retreat. The Mafia doesn’t take days off."
            ),
            _(
                "{member.display_name} thought a new passport would help. The Mafia has connections at every border."
            ),
            _(
                "{member.display_name} tried to hide in an industrial complex. The Mafia has agents in every sector."
            ),
            _(
                "{member.display_name} attempted to blend in at a local farmers' market. The Mafia has agents in every market."
            ),
            _(
                "{member.display_name} thought a new home in a gated community would be safe. The Mafia has keys to every gate."
            ),
            _(
                "{member.display_name} tried to escape through a series of tunnels. The Mafia knows every underground passage."
            ),
            _(
                "{member.display_name} attempted to disappear into a local art studio. The Mafia has eyes on every masterpiece."
            ),
            _(
                "{member.display_name} thought joining a yoga retreat would help. The Mafia finds inner peace in their own way."
            ),
            _(
                "{member.display_name} tried to blend in at a new age convention. The Mafia knows every type of new age."
            ),
            _(
                "{member.display_name} attempted to escape through a regional park. The Mafia has trackers in all the wild."
            ),
            _(
                "{member.display_name} thought they could hide in a film festival. The Mafia has cameras everywhere."
            ),
            _(
                "{member.display_name} tried to escape by blending in at a local concert. The Mafia knows all the hits."
            ),
            _(
                "{member.display_name} attempted to disappear in a remote village. The Mafia has eyes in every village."
            ),
            _(
                "{member.display_name} thought a disguise would work at a local theater. The Mafia sees every act."
            ),
            _(
                "{member.display_name} tried to hide in a historic mansion. The Mafia has keys to every mansion."
            ),
            _(
                "{member.display_name} attempted to escape through a private airfield. The Mafia controls all air traffic."
            ),
            _(
                "{member.display_name} thought they could avoid the Mafia by changing their diet. The Mafia has a taste for all changes."
            ),
            _(
                "{member.display_name} tried to blend in at a scientific conference. The Mafia has connections in every field."
            ),
            _(
                "{member.display_name} attempted to disappear at a local brewery. The Mafia controls all the taps."
            ),
            _(
                "{member.display_name} thought relocating to a secluded island would save them. The Mafia has reach everywhere."
            ),
            _(
                "{member.display_name} tried to hide in a local music store. The Mafia knows all the notes."
            ),
            _(
                "{member.display_name} attempted to escape through a labyrinthine market. The Mafia knows every stall and alley."
            ),
            _(
                "{member.display_name} thought they could avoid detection by hiding in a small town’s diner. The Mafia’s network includes diners."
            ),
            _(
                "{member.display_name} tried to blend in at a local garden center. The Mafia has green thumbs and sharp eyes."
            ),
            _(
                "{member.display_name} attempted to escape via a luxury yacht. The Mafia’s influence extends to the high seas."
            ),
            _(
                "{member.display_name} thought they could hide in a secluded cabin. The Mafia can track even the most remote locations."
            ),
            _(
                "{member.display_name} tried to disappear in a local park. The Mafia has a way of finding every green space."
            ),
            _(
                "{member.display_name} attempted to escape through a network of safe houses. The Mafia has every safe house on their radar."
            ),
            _(
                "{member.display_name} thought they could avoid the Mafia by blending in at a trade show. The Mafia has eyes on every booth."
            ),
            _(
                "{member.display_name} tried to hide in a rooftop garden. The Mafia has access to all heights."
            ),
            _(
                "{member.display_name} attempted to escape through a private vineyard. The Mafia controls every vintage."
            ),
            _(
                "{member.display_name} thought they could blend in at a local antique store. The Mafia knows every piece."
            ),
            _(
                "{member.display_name} tried to disappear in a crowded amusement park. The Mafia has surveillance on every ride."
            ),
            _(
                "{member.display_name} attempted to escape via a local ferry. The Mafia owns all the boats."
            ),
            _(
                "{member.display_name} thought they could hide in a large, bustling market. The Mafia always finds the crowd."
            ),
            _(
                "{member.display_name} tried to avoid detection by relocating to a historic district. The Mafia has history everywhere."
            ),
            _(
                "{member.display_name} attempted to disappear into a local cultural festival. The Mafia is always part of the celebration."
            ),
            _(
                "{member.display_name} thought they could avoid the Mafia by hiding in a high-end boutique. The Mafia has fashion connections."
            ),
            _(
                "{member.display_name} tried to blend in at a local aquarium. The Mafia sees every fin and scale."
            ),
            _(
                "{member.display_name} attempted to escape by taking a private tour. The Mafia controls all the tours."
            ),
            _(
                "{member.display_name} thought relocating to a ski resort would be safe. The Mafia tracks every snowflake."
            ),
            _(
                "{member.display_name} tried to disappear in a secluded vineyard. The Mafia has access to every grape."
            ),
            _(
                "{member.display_name} attempted to hide in an exclusive country club. The Mafia has memberships everywhere."
            ),
            _(
                "{member.display_name} thought they could avoid the Mafia by relocating to a mountain retreat. The Mafia knows every peak."
            ),
            _(
                "{member.display_name} tried to escape through a complex network of caves. The Mafia has maps of every underground route."
            ),
            _(
                "{member.display_name} attempted to blend in at a local arts festival. The Mafia sees through every artifice."
            ),
            _(
                "{member.display_name} thought they could escape by moving to a remote fishing village. The Mafia controls all the coasts."
            ),
            _(
                "{member.display_name} tried to disappear in a crowded convention center. The Mafia knows how to find the hidden."
            ),
            _(
                "{member.display_name} attempted to escape through a network of hidden rooms. The Mafia knows every secret passage."
            ),
            _(
                "{member.display_name} thought they could hide in a local museum. The Mafia has eyes on every exhibit."
            ),
            _(
                "{member.display_name} tried to escape via a scenic train route. The Mafia controls all scenic views."
            ),
            _(
                "{member.display_name} attempted to blend in at a local farm. The Mafia knows every barn and silo."
            ),
            _(
                "{member.display_name} thought relocating to a remote cabin would help. The Mafia tracks every move."
            ),
            _(
                "{member.display_name} tried to escape by blending in at a local zoo. The Mafia watches every animal."
            ),
            _(
                "{member.display_name} attempted to hide in a remote mountain lodge. The Mafia has access to every peak."
            ),
            _(
                "{member.display_name} thought they could avoid the Mafia by blending in at a local car show. The Mafia has eyes on every vehicle."
            ),
            _(
                "{member.display_name} tried to disappear in a crowded city park. The Mafia knows every inch of the green space."
            ),
            _(
                "{member.display_name} attempted to escape through a series of underground bunkers. The Mafia knows every bunker."
            ),
            _(
                "{member.display_name} thought they could hide at a historic battlefield. The Mafia knows every old skirmish."
            ),
            _(
                "{member.display_name} tried to blend in at a local botanical garden. The Mafia has a green thumb for finding hiding places."
            ),
            _(
                "{member.display_name} attempted to disappear during a major city event. The Mafia controls all major gatherings."
            ),
            _(
                "{member.display_name} thought a disguise at a masquerade ball would work. The Mafia always sees through masks."
            ),
            _(
                "{member.display_name} tried to escape via a private ski chalet. The Mafia has access to all resorts."
            ),
            _(
                "{member.display_name} attempted to hide in an upscale gallery. The Mafia knows every art dealer."
            ),
            _(
                "{member.display_name} thought relocating to a remote cottage would help. The Mafia tracks every retreat."
            ),
            _(
                "{member.display_name} tried to disappear into a crowded street fair. The Mafia knows every street corner."
            ),
            _(
                "{member.display_name} attempted to blend in at a local opera house. The Mafia sees through every performance."
            ),
            _(
                "{member.display_name} thought they could escape by taking a scenic boat ride. The Mafia owns every waterway."
            ),
            _(
                "{member.display_name} tried to hide in a busy metropolitan area. The Mafia knows every city block."
            ),
            _(
                "{member.display_name} attempted to disappear into a local airport. The Mafia has eyes on every departure."
            ),
            _(
                "{member.display_name} thought blending in at a charity auction would work. The Mafia has all the bidders."
            ),
            _(
                "{member.display_name} tried to escape through a local observatory. The Mafia keeps watch from the stars."
            ),
            _(
                "{member.display_name} attempted to hide in a remote lighthouse. The Mafia has beacons everywhere."
            ),
            _(
                "{member.display_name} thought they could avoid detection by moving to a small island. The Mafia’s reach is global."
            ),
            _(
                "{member.display_name} tried to blend in at a local fitness center. The Mafia can spot anyone trying to change their routine."
            ),
            _(
                "{member.display_name} attempted to escape through a series of interconnected caves. The Mafia knows every path."
            ),
            _(
                "{member.display_name} thought relocating to a small town would be safe. The Mafia has agents in every town."
            ),
            _(
                "{member.display_name} tried to disappear in a bustling city subway. The Mafia controls all transit systems."
            ),
            _(
                "{member.display_name} attempted to hide in a local pet shop. The Mafia sees through every cute face."
            ),
            _(
                "{member.display_name} thought a disguise would work at a local music festival. The Mafia knows all the tunes."
            ),
            _(
                "{member.display_name} tried to escape by blending in at a high-end fashion show. The Mafia sets all the trends."
            ),
            _(
                "{member.display_name} attempted to disappear in a local tech startup. The Mafia has connections in every sector."
            ),
            _(
                "{member.display_name} thought hiding in a local orchard would help. The Mafia knows every fruit-bearing tree."
            ),
            _(
                "{member.display_name} tried to hide in a local vineyard. The Mafia controls every bottle and grape."
            ),
            _(
                "{member.display_name} attempted to escape through a series of historical landmarks. The Mafia knows all the landmarks."
            ),
            _(
                "{member.display_name} thought they could avoid detection by blending in at a local culinary school. The Mafia knows every dish."
            ),
            _(
                "{member.display_name} tried to escape via a private vineyard. The Mafia tracks every vintage."
            ),
            _(
                "{member.display_name} attempted to hide in a busy city square. The Mafia keeps tabs on every corner."
            ),
            _(
                "{member.display_name} thought a disguise at a local fundraiser would work. The Mafia sees through all the charm."
            ),
            _(
                "{member.display_name} tried to disappear in a local library’s special collections. The Mafia has a catalog of every secret."
            ),
            _(
                "{member.display_name} attempted to escape through a network of old mining tunnels. The Mafia has maps of every mine."
            ),
            _(
                "{member.display_name} thought relocating to a coastal lighthouse would help. The Mafia controls every beacon."
            ),
            _(
                "{member.display_name} tried to blend in at a local outdoor market. The Mafia knows every vendor and stall."
            ),
            _(
                "{member.display_name} attempted to disappear during a high-profile charity gala. The Mafia has agents at every event."
            ),
            _(
                "{member.display_name} thought they could avoid the Mafia by blending in at a large-scale convention. The Mafia controls every delegate."
            ),
            _(
                "{member.display_name} tried to hide in a local rock climbing gym. The Mafia has eyes on every ascent."
            ),
            _(
                "{member.display_name} attempted to escape through a series of old railway tunnels. The Mafia knows every track."
            ),
            _(
                "{member.display_name} thought relocating to a remote ranch would be safe. The Mafia has reach even in the wild."
            ),
            _(
                "{member.display_name} tried to disappear at a local fireworks display. The Mafia controls every explosion."
            ),
            _(
                "{member.display_name} attempted to blend in at a local jazz club. The Mafia knows every note and chord."
            ),
            _(
                "{member.display_name} thought hiding in a local botanical garden would work. The Mafia sees through every leaf and petal."
            ),
            _(
                "{member.display_name} tried to escape via a remote luxury resort. The Mafia has agents everywhere, even in paradise."
            ),
            _(
                "{member.display_name} attempted to disappear in a local arcade. The Mafia controls all the high scores."
            ),
            _(
                "{member.display_name} thought they could avoid detection by blending in at a local agricultural fair. The Mafia has their eyes on every stall."
            ),
            _(
                "{member.display_name} tried to hide in a crowded city plaza. The Mafia can find you in the midst of a crowd."
            ),
            _(
                "{member.display_name} attempted to escape through a network of private tunnels. The Mafia has access to all secret paths."
            ),
            _(
                "{member.display_name} thought relocating to a mountain retreat would be safe. The Mafia tracks every peak."
            ),
            _(
                "{member.display_name} tried to disappear during a high-profile fashion event. The Mafia has a sense for all the high styles."
            ),
            _(
                "{member.display_name} attempted to blend in at a local art studio. The Mafia sees through every brushstroke."
            ),
            _(
                "{member.display_name} thought they could avoid the Mafia by hiding in a local zoo. The Mafia has their eyes on every enclosure."
            ),
            _(
                "{member.display_name} tried to escape via a remote countryside estate. The Mafia has reach into every corner of the country."
            ),
            _(
                "{member.display_name} attempted to hide in a local gymnasium. The Mafia can spot anyone trying to break a sweat."
            ),
        ]
    ).format(member=member)
