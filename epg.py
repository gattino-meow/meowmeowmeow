import urllib.request
import urllib.parse
import json
import gzip
import html
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

# Configurazioni
PROXY_ENDPOINT = 'https://guidatv-omega.vercel.app/api/epgprime'
BASE_URL = 'https://www.primevideo.com'
START_URL = f'{BASE_URL}/livetv?dvWebAppClientVersion=1.0.120753.0'
OUTPUT_FILE = 'prime_epg.xml.gz'

def fetch_json(url):
    """Scarica il JSON dall'API passando per il bridge Vercel che usa PROXY_URL."""
    # Se l'URL non è quello di partenza, lo passiamo come parametro 'next'
    if url == START_URL:
        request_url = PROXY_ENDPOINT
    else:
        encoded_target = urllib.parse.quote_plus(url)
        request_url = f"{PROXY_ENDPOINT}?next={encoded_target}"

    req = urllib.request.Request(request_url)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Errore durante la richiesta al bridge Vercel: {e}")
        return None

def format_xmltv_time(ms):
    """Converte i millisecondi nel formato XMLTV (UTC)."""
    dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    return dt.strftime('%Y%m%d%H%M%S +0000')

def parse_xmltv_time(time_str):
    """Converte la stringa XMLTV in datetime (UTC)."""
    return datetime.strptime(time_str[:14], '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)

def load_existing_epg(cutoff_dt):
    """Carica l'XML precedente, mantenendo solo i programmi più recenti."""
    channels = {}
    programmes = {}
    
    if not os.path.exists(OUTPUT_FILE):
        return channels, programmes

    print("Lettura storico dal file XML esistente...")
    try:
        with gzip.open(OUTPUT_FILE, 'rt', encoding='utf-8') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            
            for ch in root.findall('channel'):
                ch_id = ch.attrib.get('id')
                if ch_id:
                    channels[ch_id] = ET.tostring(ch, encoding='unicode')
            
            for prog in root.findall('programme'):
                stop_str = prog.attrib.get('stop', '')
                if stop_str:
                    stop_dt = parse_xmltv_time(stop_str)
                    if stop_dt > cutoff_dt:
                        ch_id = prog.attrib.get('channel')
                        start_str = prog.attrib.get('start')
                        programmes[(ch_id, start_str)] = ET.tostring(prog, encoding='unicode')
    except Exception as e:
        print(f"Avviso: impossibile leggere l'EPG esistente. Errore: {e}")

    print(f"Recuperati {len(programmes)} programmi validi dallo storico.")
    return channels, programmes

def generate_epg():
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=1)
    channels_dict, programmes_dict = load_existing_epg(cutoff_dt)
    
    print("Inizio download nuovi dati tramite Bridge Vercel + Proxy...")
    current_url = START_URL
    page_count = 1
    
    while current_url:
        print(f"Scaricamento pagina {page_count}...")
        data = fetch_json(current_url)
        
        if not data:
            break
            
        body = data.get('body', {})
        containers = body.get('containers', [])
        
        for container in containers:
            if container.get('containerType') != 'EpgGroup':
                continue
                
            for entity in container.get('entities', []):
                station = entity.get('station')
                if not station:
                    continue
                
                ch_name_raw = station.get('name', 'Unknown')
                ch_id = ch_name_raw.replace(' ', '').replace('-', '').replace("'", '')
                ch_name = html.escape(ch_name_raw)
                ch_logo = html.escape(station.get('logo', ''))
                
                ch_xml = f'  <channel id="{ch_id}">\n    <display-name>{ch_name}</display-name>'
                if ch_logo:
                    ch_xml += f'\n    <icon src="{ch_logo}" />'
                ch_xml += '\n  </channel>'
                channels_dict[ch_id] = ch_xml
                
                for prog in station.get('schedule', []):
                    start_ms = prog.get('start')
                    end_ms = prog.get('end')
                    stop_dt = datetime.fromtimestamp(end_ms / 1000.0, tz=timezone.utc)
                    
                    if stop_dt <= cutoff_dt:
                        continue
                        
                    start_str = format_xmltv_time(start_ms)
                    end_str = format_xmltv_time(end_ms)
                    
                    meta = prog.get('metadata', {})
                    raw_title = meta.get('title', '')
                    series_title = meta.get('seriesTitle', '')
                    
                    if series_title:
                        main_title = series_title
                        sub_title = raw_title if raw_title and raw_title != series_title else ""
                    else:
                        main_title = raw_title
                        sub_title = ""
                        
                    main_title = html.escape(main_title)
                    sub_title = html.escape(sub_title)
                    
                    synopsis = meta.get('synopsis', '')
                    year = meta.get('releaseYear', '')
                    desc = synopsis
                    if year:
                        desc = f"{synopsis} ({year})" if synopsis else str(year)
                    desc = html.escape(desc)
                    
                    img = meta.get('modalImage', {}).get('url') or meta.get('image', {}).get('url', '')
                    img = html.escape(img)
                    rating = html.escape(meta.get('contentMaturityRating', {}).get('rating', ''))
                    badge_label = meta.get('linearBadge', {}).get('label', '')
                    is_live = True if badge_label == "LIVE" or meta.get('linearBadge', {}).get('isLive') else False
                    
                    prog_xml = [f'  <programme start="{start_str}" stop="{end_str}" channel="{ch_id}">']
                    prog_xml.append(f'    <title>{main_title}</title>')
                    if sub_title: prog_xml.append(f'    <sub-title>{sub_title}</sub-title>')
                    if desc: prog_xml.append(f'    <desc>{desc}</desc>')
                    if img: prog_xml.append(f'    <icon src="{img}" />')
                    if rating: prog_xml.append(f'    <rating><value>{rating}</value></rating>')
                    if is_live: prog_xml.append(f'    <category>Live</category>')
                    prog_xml.append('  </programme>')
                    
                    programmes_dict[(ch_id, start_str)] = '\n'.join(prog_xml)
        
        pagination_url = body.get('pagination', {}).get('url')
        if pagination_url:
            current_url = BASE_URL + pagination_url
            page_count += 1
            time.sleep(1) # Delay per non sovraccaricare il bridge
        else:
            current_url = None

    print(f"Salvataggio... ({len(channels_dict)} canali, {len(programmes_dict)} programmi)")
    sorted_programmes = [programmes_dict[k] for k in sorted(programmes_dict.keys())]
    
    final_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n' + \
                '\n'.join(channels_dict.values()) + '\n' + \
                '\n'.join(sorted_programmes) + '\n</tv>'
                
    with gzip.open(OUTPUT_FILE, 'wt', encoding='utf-8', compresslevel=9) as f:
        f.write(final_xml)
        
    print(f"Finito! File: {OUTPUT_FILE}")

if __name__ == '__main__':
    generate_epg()