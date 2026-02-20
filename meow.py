import requests
import re
import os
import time

def extract_stream_link(url, pattern=r'"(https://[^"]+\.m3u8[^"]*)"'):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://sanmarinortv.sm/"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        match = re.search(pattern, response.text)
        if match:
            return match.group(1).replace('\\/', '/')
    except Exception as e:
        print(f"Errore su {url}: {e}")
    return None

def create_master_m3u8(filename, stream_url, resolution="1280x720", bandwidth="2000000"):
    if not stream_url:
        return
    content = (
        "#EXTM3U\n"
        "#EXT-X-VERSION:3\n"
        f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution}\n"
        f"{stream_url}\n"
    )
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

def check_update_needed(timestamp_file):
    if not os.path.exists(timestamp_file):
        return True
    
    try:
        with open(timestamp_file, "r") as f:
            last_time = float(f.read().strip())
        
        current_time = time.time()
        # 86400 secondi = 24 ore
        if (current_time - last_time) > 86400:
            return True
    except:
        return True
        
    return False

def update_timestamp(timestamp_file):
    with open(timestamp_file, "w") as f:
        f.write(str(time.time()))

def main():
    # San Marino TV
    url_tv = "https://catchup.acdsolutions.it/jstag/videoplayerLiveFluid/TV?ch=0&eID=livePlayerPageElement&vID=666666666&autoPlay=true"
    link_tv = extract_stream_link(url_tv)
    create_master_m3u8("sanm_tv.m3u8", link_tv)

    # San Marino Sport
    url_sport = "https://catchup.acdsolutions.it/jstag/videoplayerLiveFluid/TV?ch=1&eID=livePlayerPageElement&vID=666666666&autoPlay=true"
    link_sport = extract_stream_link(url_sport)
    create_master_m3u8("sanm_sport.m3u8", link_sport)

    # DonnaTV
    ts_file = "last_update_donnatv.txt"
    if check_update_needed(ts_file):
        print("DonnaTV: aggiornamento in corso...")
        url_donnatv = "https://donnatv.com/video/viewlivestreaming?rel=34959&cntr=0"
        # Cerco il link m3u8 dentro l'attributo src
        pattern_donnatv = r'src="(https://[^"]+\.m3u8[^"]*)"'
        link_donnatv = extract_stream_link(url_donnatv, pattern_donnatv)
        
        if link_donnatv:
            create_master_m3u8("donnatv.m3u8", link_donnatv, resolution="1024x576", bandwidth="1600000")
            update_timestamp(ts_file)
    else:
        print("DonnaTV: link ancora valido, salto l'aggiornamento.")

if __name__ == "__main__":
    main()
