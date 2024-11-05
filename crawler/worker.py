from threading import Thread, Lock

from inspect import getsource
from utils.download import download
from utils import get_logger
import scraper
import time

# Added content
from scraper import custom_hash, compute_simhash, hamming_distance, extract_text_from_html
from urllib.parse import urlparse
checksums = set()
simhashes = []
similarity_threshold = 3

class Worker(Thread):
    def __init__(self, worker_id, config, frontier):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        # basic check for requests in scraper
        assert {getsource(scraper).find(req) for req in {"from requests import", "import requests"}} == {-1}, "Do not use requests in scraper.py"
        assert {getsource(scraper).find(req) for req in {"from urllib.request import", "import urllib.request"}} == {-1}, "Do not use urllib.request in scraper.py"
        super().__init__(daemon=True)
        
    def run(self):
        global checksums, simhashes

        while True:
            try:
                tbd_url = self.frontier.get_tbd_url()
                if not tbd_url:
                    self.logger.info("Frontier is empty. Stopping Crawler.")
                    break
                resp = download(tbd_url, self.config, self.logger)
                self.logger.info(
                    f"Downloaded {tbd_url}, status <{resp.status}>, "
                    f"using cache {self.config.cache_server}.")
    	    
    	    # Check connection status
                if resp.status == 200 and resp.raw_response and resp.raw_response.content:
                    text = extract_text_from_html(resp.raw_response.content)
    	    
    	    	# Check exact duplication
                    checksum = custom_hash(text)
    	    	# Check near duplication
                    simhash = compute_simhash(text)
    
    		# Thread safe
                    with Lock():
                        if checksum in checksums or any(hamming_distance(simhash, existing_simhash) <= similarity_threshold for existing_simhash in simhashes):
                            self.logger.info(f"Page at {tbd_url} is a near-duplicate. Skipping.")
                            self.frontier.mark_url_complete(tbd_url)
                            continue
    		
                        checksums.add(checksum)
                        simhashes.append(simhash)
    
    
                scraped_urls = scraper.scraper(tbd_url, resp)
                for scraped_url in scraped_urls:
                    self.frontier.add_url(scraped_url)
                self.frontier.mark_url_complete(tbd_url)
                time.sleep(self.config.time_delay)
            except:
                  self.logger.error(f"An error occurred: {e}")

