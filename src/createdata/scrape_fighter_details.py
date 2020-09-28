import pickle
from typing import Dict, List

import numpy as np
import pandas as pd

from src.createdata.make_soup import make_soup
from src.createdata.print_progress import print_progress

from src.createdata.data_files_path import (  # isort:skip
    FIGHTER_DETAILS,
    PAST_FIGHTER_LINKS_PICKLE_PATH,
)


class FighterDetailsScraper:
    def __init__(self):
        self.HEADER = ["Height", "Weight", "Reach", "Stance", "DOB"]
        self.FIGHTER_DETAILS_PATH = FIGHTER_DETAILS

        print("Getting fighter urls \n")
        self.fighter_group_urls = self._get_fighter_group_urls()
        print("Getting fighter names and details \n")
        self.new_fighter_links, self.all_fighter_links = (
            self._get_updated_fighter_links()
        )

    def _get_fighter_group_urls(self) -> List[str]:
        alphas = [chr(i) for i in range(ord("a"), ord("a") + 26)]
        fighter_group_urls = [
            f"http://ufcstats.com/statistics/fighters?char={alpha}&page=all"
            for alpha in alphas
        ]
        return fighter_group_urls

    def _get_fighter_name_and_link(self,) -> Dict[str, List[str]]:
        fighter_name_and_link = {}
        fighter_name = ""

        l = len(self.fighter_group_urls)
        print("Scraping all fighter names and links: ")
        print_progress(0, l, prefix="Progress:", suffix="Complete")

        for index, fighter_group_url in enumerate(self.fighter_group_urls):
            soup = make_soup(fighter_group_url)
            table = soup.find("tbody")
            names = table.findAll(
                "a", {"class": "b-link b-link_style_black"}, href=True
            )
            for i, name in enumerate(names):
                if (i + 1) % 3 != 0:
                    if fighter_name == "":
                        fighter_name = name.text
                    else:
                        fighter_name = fighter_name + " " + name.text
                else:
                    fighter_name_and_link[fighter_name] = name["href"]
                    fighter_name = ""
            print_progress(index + 1, l, prefix="Progress:", suffix="Complete")

        return fighter_name_and_link

    def _get_updated_fighter_links(self):
        all_fighter_links = self._get_fighter_name_and_link()

        if not PAST_FIGHTER_LINKS_PICKLE_PATH.exists():
            # if no past event links are present, then there are no new event links
            new_fighter_links = {}
        else:
            # get past event links
            pickle_in = open(PAST_FIGHTER_LINKS_PICKLE_PATH.as_posix(), "rb")
            past_event_links = pickle.load(pickle_in)
            pickle_in.close()

            # Find links of the newer fighters
            new_fighter_links = list(
                set(all_fighter_links.keys()) - set(past_event_links.keys())
            )

        # dump all_event_links as PAST_EVENT_LINKS
        pickle_out1 = open(PAST_FIGHTER_LINKS_PICKLE_PATH.as_posix(), "wb")
        pickle.dump(all_fighter_links, pickle_out1)
        pickle_out1.close()

        return new_fighter_links, all_fighter_links

    def _get_fighter_name_and_details(
        self, fighter_name_and_link: Dict[str, List[str]]
    ) -> pd.DataFrame:
        fighter_name_and_details = {}

        l = len(fighter_name_and_link)
        print("Scraping all fighter data: ")
        print_progress(0, l, prefix="Progress:", suffix="Complete")

        for index, (fighter_name, fighter_url) in enumerate(
            fighter_name_and_link.items()
        ):
            another_soup = make_soup(fighter_url)
            divs = another_soup.findAll(
                "li",
                {"class": "b-list__box-list-item b-list__box-list-item_type_block"},
            )
            data = []
            for i, div in enumerate(divs):
                if i == 5:
                    break
                data.append(
                    div.text.replace("  ", "")
                    .replace("\n", "")
                    .replace("Height:", "")
                    .replace("Weight:", "")
                    .replace("Reach:", "")
                    .replace("STANCE:", "")
                    .replace("DOB:", "")
                )

            fighter_name_and_details[fighter_name] = data
            print_progress(index + 1, l, prefix="Progress:", suffix="Complete")

        df = (
            pd.DataFrame(fighter_name_and_details)
            .T.replace("--", value=np.NaN)
            .replace("", value=np.NaN)
        )
        df.columns = self.HEADER

        return df

    def create_fighter_data_csv(self) -> None:

        if not self.new_fighter_links:
            if self.FIGHTER_DETAILS_PATH.exists():
                print("No new fighter data to scrape at the moment!")
                return
            else:
                fighter_details_df = self._get_fighter_name_and_details(
                    self.all_fighter_links
                )
        else:
            new_fighter_details_df = self._get_fighter_name_and_details(
                self.new_fighter_links
            )

            old_fighter_details_df = pd.read_csv(self.FIGHTER_DETAILS_PATH)

            fighter_details_df = new_fighter_details_df.append(
                old_fighter_details_df, ignore_index=True
            )

        fighter_details_df.to_csv(self.FIGHTER_DETAILS_PATH, index_label="fighter_name")
        print("Successfully scraped and saved ufc fighter data!\n")
