import requests
import re

def extract_stream_link(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://sanmarinortv.sm/"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        pattern = r'"(https://[^"]+\.m3u8[^"]*)"'
        match = re.search(pattern, response.text)
        if match:
            return match.group(1).replace('\\/', '/')
    except Exception as e:
        print(f"Errore su {url}: {e}")
    return None

def create_master_m3u8(filename, stream_url):
    if not stream_url:
        return
    # Struttura di un Master Playlist HLS minimale
    content = (
        "#EXTM3U\n"
        "#EXT-X-VERSION:3\n"
        "#EXT-X-STREAM-INF:BANDWIDTH=2000000,RESOLUTION=1280x720\n"
        f"{stream_url}\n"
    )
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    # Canale TV Normale
    url_tv = "https://catchup.acdsolutions.it/jstag/videoplayerLiveFluid/TV?ch=0&eID=livePlayerPageElement&vID=666666666&autoPlay=true"
    link_tv = extract_stream_link(url_tv)
    create_master_m3u8("sanm_tv.m3u8", link_tv)

    # Canale Sport
    url_sport = "https://catchup.acdsolutions.it/jstag/videoplayerLiveFluid/TV?ch=1&eID=livePlayerPageElement&vID=666666666&autoPlay=true"
    link_sport = extract_stream_link(url_sport)
    create_master_m3u8("sanm_sport.m3u8", link_sport)

if __name__ == "__main__":
    main()
