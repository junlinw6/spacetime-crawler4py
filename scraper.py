import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

def custom_hash(text):
    #计算文本的简单哈希值
    return hash(text)

def compute_simhash(text):
    #计算文本的 simhash
    words = text.split()
    hash_bits = [0] * 64  # 假设使用 64 位

    for word in words:
        word_hash = custom_hash(word)
        for i in range(64):
            bit = (word_hash >> i) & 1
            if bit == 1:
                hash_bits[i] += 1
            else:
                hash_bits[i] -= 1

    # 将 hash_bits 转换为 simhash
    simhash = 0
    for i in range(64):
        if hash_bits[i] > 0:
            simhash |= (1 << i)

    return simhash

def hamming_distance(hash1, hash2):
    #计算两个 simhash 值之间的汉明距离
    x = hash1 ^ hash2  # 异或操作，找出不同的位
    distance = 0
    while x:
        distance += x & 1
        x >>= 1
    return distance

def extract_text_from_html(html_content):
    #从 HTML 内容中提取纯文本
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text()


def has_sufficient_text(content):
    soup = BeautifulSoup(content, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    words = text.split()
    return len(words) > 20 # 假设50个单词以上视为有足够内容

def scraper(url, resp):
    if resp.status != 200 or not resp.raw_response.content:
        return []
    
    if not has_sufficient_text(resp.raw_response.content):
        return [] #页面内容过少时直接跳过

    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]


def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    
    # Parses the web page and extracts valid URLs from the response.
    if resp.status != 200 or not resp.raw_response.content:
        return []

    # Extracts hyperlinks from the response content.
    links = []
    try:
        soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            # Convert relative URLs to absolute URLs
            full_url = urljoin(url, href)
            # Remove fragment identifiers (e.g., #section)
            full_url = full_url.split('#')[0]
            links.append(full_url)
    except Exception as e:
        print(f"Error parsing links from {url}: {e}")
    return links

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
    
     # Only allow URLs from specific UCI domains
        if not re.match(
            r".*\.(ics\.uci\.edu|cs\.uci\.edu|informatics\.uci\.edu|stat\.uci\.edu|today\.uci\.edu).*"
            r"|today\.uci\.edu\/department\/information_computer_sciences\/",
            parsed.netloc):
            return False

        if re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()):
            return False
    
        #Checks for traps
        if re.search(r'(calendar|page|sort|refid)=', parsed.query.lower()):
            return False
    
        return True
        
    except TypeError:
        print ("TypeError for ", parsed)
        raise
