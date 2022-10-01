#!/bin/bash
# Copyright (c) 2022 Warren Usui
# This code is licensed under the MIT license (see LICENSE.txt for details)
"""
This script answers the ultimate question that I have found to be the most
pressing issue of our times:

Has any major league pitcher won games against the Boston Braves,
Milwaukee Braves, and Atlanta Braves?

It turns out that the answer is yes.  One pitcher, Robin Roberts, has
accomplished this feat.  It also turns out that he is the only pitcher
who has done this, and this program demonstrates that.

I say demonstrates rather than proves because I have made a couple of
assumptions here:

1.) http://www.baseball-reference.com is accurate (I have 99.9% confidence
    that this is true)
2.) I have not ventured through a warp in the space-time continuum into a
    parallel universe where another pitcher has also accomplished this feat
    (I have 99.7% confidence that I am still in the same universe)

So after this program scrapes all the important data, it produces a table
of all possible pitchers who could have accomplished this feat, and lists
the Boston, Milwaukee, and Atlanta teams that they have wins against.

In order to be considered possibly able to accomplish this feat, I made sure
of the following:
     1. The player was a pitcher (duh).
     2. The player's MLB career started before 1953.
     3. The player's MLB career ended after 1965.

The above three items are true for seventeen individuals.  These are
the players whose names are listed in the table that is output.
"""
import uuid
import webbrowser
import requests
from bs4 import BeautifulSoup
import pandas as pd
HTML_PAGES = "https://www.baseball-reference.com"
FIRST_MOVE = 1953
LAST_MOVE = 1966

def pack_player(link, name, years):
    """
    Pack player information into a diictionary

    Input:
        link: partial url of this player's page
        name: player's name
        years: career years formatted as "(xxxx-yyyy)"

    Returns:
        A dictionary containing the link, name, first and last year values
        to be added to the value passed back  from scan_inactive_players.
    """
    retv = {}
    retv["link"] = link
    retv["name"] = name
    syears = years.strip().split("-")
    retv["first"] = int(syears[0].split("(")[-1])
    retv["last"] = int(syears[1].split(")")[0])
    return retv

def pl_id(plindex):
    """
    Extract player's id from the URL

    Input:
        plindex -- player's url

    Return:
        Seven character player id string used by Baseball Reference
    """
    splt1 = plindex.split("/")[-1]
    splt2 = splt1.split(".")[0]
    return splt2

def scan_inactive_players():
    """
    Scan all the players on the baseball reference site and find all
    possible players whose career start and end dates indicate that
    they could have played against the Boston, Milwaukee, and Atlanta
    Braves.  Note that the parsing done here does not find active players
    because those names are nested inside html used to make their text bold.
    For the purpose of finding players who could have played against the
    Boston Braves, an active player today would have to have played for 70
    years, so this flaw in the parsing does not affect the results of the
    old pitcher search.

    This routine returns a dictionary indexed by the Baseball Reference
    player id.  Each entry is a dictionary consisting of four named values:
        link: a link to the url of the player's page
        name: the name of the player
        first: integer value of the year this player's career started
        last: integer value of the last year of this player's career
    """
    retv = {}
    for flet in "abcdefghijklmnopqrstuvwxyz":
        apage = f"{HTML_PAGES}/players/{flet}"
        resp = requests.get(apage)
        soup = BeautifulSoup(resp.text, "html.parser")
        info = soup.find_all("p")
        for entry in info:
            if len(entry.contents) < 2:
                continue
            plyr_ref = entry.find(href=True)
            if plyr_ref is None:
                continue
            try:
                hrefv =  entry.contents[0]['href']
            except TypeError:
                continue
            if not hrefv.startswith("/players/"):
                continue
            if not hrefv.endswith(".shtml"):
                continue
            ppacket = pack_player(hrefv, plyr_ref.contents[0],
                                  entry.contents[1])
            retv[pl_id(hrefv)] = ppacket
    return retv

def not_a_pit(br_id):
    """
    Test used to weed out non-pitchers from the list of players to check

    Input:
        br_id -- Baseball Reference player id:
    Return:
        True if this player has no pitching stats
    """
    initl = br_id[0]
    urlv = f"{HTML_PAGES}/players/{initl}/{br_id}.shtml"
    resp = requests.get(urlv)
    if resp.text.find("Standard Pitching") < 0:
        return True
    return False

def find_p_in_right_time_period():
    """
    Look through all the players.  Return only those players that
    are pitchers who have played in the right time periods (before 1953
    and after 1965).
    """
    retpit = {}
    pl_data = scan_inactive_players()
    for entry in pl_data.items():
        indp = entry[1]
        if indp['first'] >= FIRST_MOVE:
            continue
        if indp['last'] < LAST_MOVE:
            continue
        if not_a_pit(entry[0]):
            continue
        retpit[entry[0]] = pl_data[entry[0]]
    return retpit

def get_team_game_table(yearv, tabbrev):
    """
    Given a year and a team abbreviation (BSN for Boston, MLN for Milwaukee,
    and ATL for Atlanta), find the web page for that team's schedule and
    return the results table.
    """
    web_page = f"{HTML_PAGES}/teams/{tabbrev}/{yearv}"
    web_page += "-schedule-scores.shtml"
    resp = requests.get(web_page)
    soup = BeautifulSoup(resp.text, "html.parser")
    tablev = soup.find('table', id="team_schedule")
    return tablev

def check_range(checker_list, yranges):
    """
    Find pitcher wins by scanning all possible Braves games in a time period

    Input:
        checker_list: List of player id's of eligible pitchers
        yranges: list of lists.  Each list entry at the top level represents
                 a city.  Each entry in that list contains the first and
                 last years that need to be checked in order to find
                 pitchers who have beaten the Braves in a specific city

    Returns:
        dictionary indexed by player ids.  The data inside those player
        ids is a list of cities that that player has had wins against.
    """
    answer = {}
    for entry in checker_list:
        answer[entry] = []
    tabbrev = ['BSN', 'MLN', 'ATL']
    for count, rngvals in enumerate(yranges):
        for yearv in range(rngvals[0], rngvals[1]):
            tablev = get_team_game_table(yearv, tabbrev[count])
            for row in tablev.tbody.find_all('tr'):
                columns = row.find_all('td')
                if len(columns) < 12:
                    continue
                if columns[5].text.startswith("L"):
                    plyrw = columns[12].find('a')['href'].split("/")[-1]
                    pname = plyrw.split('.')[0]
                    if pname in checker_list:
                        answer[pname].append(tabbrev[count])
    return answer

def html_display(answer, pdata):
    """
    Display the result as an html table on the browser

    Input:
        answer: Results collected by the rest of the code in
        the_search_for_all_three
        pdata: Table of players.  Used to get player's name into the table.

    Creates a local file that gets displayed on the browser.  Results
    are formatted into an html table whose columns are pitcher names
    and the teams they have beaten.
    """
    full_name = {"BSN": "Boston", "MLN": "Milwaukee", "ATL": "Atlanta"}
    output = {"Pitcher": [], "Opponents": []}
    for pit in answer.items():
        abbrev_list = list(set(pit[1]))
        city_list = []
        for entry in abbrev_list:
            city_list.append(full_name[entry])
        olist = ', '.join(city_list)
        if not olist:
            olist = "None"
        output["Pitcher"].append(pdata[pit[0]]['name'])
        output["Opponents"].append(olist)
    dframe = pd.DataFrame.from_dict(output)
    uniq_id = str(uuid.uuid4())
    ufname = f"pitchers-{uniq_id}.html"
    with open(ufname, 'w', encoding="utf8") as fdout:
        fdout.write(dframe.to_html(index=False, index_names=False))
    webbrowser.open(ufname)

def the_search_for_all_three():
    """
    Top level routine to find the pitchers that we are looking for.
    First find all pitchers whose career years make it possible for
    them to accomplish wins against all teams.  Then find the range of
    all possible games that the Braves have played that these playerrs could
    have won, and then loop for years that these players could have played
    the Braves.
    """
    pdata = find_p_in_right_time_period()
    checker_list =  list(pdata.keys())
    earliest = FIRST_MOVE - 1
    latest = LAST_MOVE
    for entry in pdata.items():
        if entry[1]['first'] < earliest:
            earliest = entry[1]['first']
        if entry[1]['last'] > latest:
            latest = entry[1]['last']
    yranges = [[earliest, FIRST_MOVE],
               [FIRST_MOVE, LAST_MOVE],
               [LAST_MOVE, latest + 1]]
    answer = check_range(checker_list, yranges)
    html_display(answer, pdata)

if __name__ == "__main__":
    the_search_for_all_three()
