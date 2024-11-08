import os
import shelve

from threading import Thread, RLock
from queue import Queue, Empty

from utils import get_logger, get_urlhash, normalize
from scraper import is_valid

#added content
from collections import deque
import time
from urllib.parse import urlparse


class Frontier(object):
    def __init__(self, config, restart):
        self.logger = get_logger("FRONTIER")
        self.config = config
        self.to_be_downloaded = deque()
        
        self.domain_last_access = {}  # Track last access time per domain
        self.lock = RLock()  # Ensure thread safety   
        
        # 确保删除所有与 shelve 相关的文件
        if restart:
            for ext in ('.dat', '.dir', '.bak', ''):
                shelve_file = self.config.save_file + ext
                if os.path.exists(shelve_file):
                    os.remove(shelve_file)
                    self.logger.info(f"Removed existing shelve file: {shelve_file}")
                    
        # 打开 shelve 文件或创建新的
        self.save = shelve.open(self.config.save_file, writeback=True)

        if not os.path.exists(self.config.save_file) and not restart:
            # Save file does not exist, but request to load save.
            self.logger.info(
                f"Did not find save file {self.config.save_file}, "
                f"starting from seed.")
        elif os.path.exists(self.config.save_file) and restart:
            # Save file does exists, but request to start from seed.
            self.logger.info(
                f"Found save file {self.config.save_file}, deleting it.")
            os.remove(self.config.save_file)
            
        # Load existing save file, or create one if it does not exist.
        self.save = shelve.open(self.config.save_file)
        if restart:
            for url in self.config.seed_urls:
                self.add_url(url)
        else:
            # Set the frontier state with contents of save file.
            self._parse_save_file()
            if not self.save:
                for url in self.config.seed_urls:
                    self.add_url(url)

    def _parse_save_file(self):
        ''' This function can be overridden for alternate saving techniques. '''
        total_count = len(self.save)
        tbd_count = 0
        for url, completed in self.save.values():
            if not completed and is_valid(url):
                self.to_be_downloaded.append(url)
                tbd_count += 1
        self.logger.info(
            f"Found {tbd_count} urls to be downloaded from {total_count} "
            f"total urls discovered.")


    
    def get_tbd_url(self):
        with self.lock:
            if self.to_be_downloaded:
                for _ in range(len(self.to_be_downloaded)):
                    url = self.to_be_downloaded.popleft()  # 从队列中移除元素
                    
                    domain = urlparse(url).netloc
                    last_access_time = self.domain_last_access.get(domain, 0)
                    current_time = time.time()
                    if current_time - last_access_time >= 0.5:
                        self.domain_last_access[domain] = current_time
                        return url
                    else:
                        self.to_be_downloaded.insert(0, url)  # Put it back for later
                        time.sleep(0.1)  # Wait before checking again
                return None
            return None

    def add_url(self, url):
        with self.lock:
            url = normalize(url)
            urlhash = get_urlhash(url)
            if urlhash not in self.save:
                self.save[urlhash] = (url, False)
                self.save.sync()
                self.to_be_downloaded.append(url)
    
    def mark_url_complete(self, url):
        with self.lock:
            urlhash = get_urlhash(url)
            if urlhash not in self.save:
                # This should not happen.
                self.logger.error(
                    f"Completed url {url}, but have not seen it before.")
    
            self.save[urlhash] = (url, True)
            self.save.sync()
