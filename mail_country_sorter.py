#!/usr/bin/env python3
import argparse
import configparser
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import sys
import threading
import csv
import logging
import socket
try:
    import tldextract
except Exception:
    tldextract = None
try:
    import geoip2.database
except Exception:
    geoip2 = None


def load_tld_map(path: Path):
    d = {}
    if not path.exists():
        return d
    for line in path.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # expected format: .ac=>Ascension Island
        if '=>' in line:
            tld, country = line.split('=>', 1)
            d[tld.strip().lower()] = country.strip()
    return d


def load_settings(path: Path):
    cfg = configparser.ConfigParser()
    res = {'ThreadCount': 10}
    if not path.exists():
        return res
    try:
        cfg.read(path, encoding='utf-8')
        if 'EMailCountrySorter' in cfg:
            res['ThreadCount'] = cfg.getint('EMailCountrySorter', 'ThreadCount', fallback=10)
    except Exception:
        pass
    return res


def find_country_for_domain(domain: str, tld_map: dict):
    domain = domain.lower().strip()
    domain = re.split(r'[:/]', domain)[0]
    # Use tldextract if available to reliably get public suffix
    suffix_candidates = []
    if tldextract:
        try:
            ext = tldextract.extract(domain)
            if ext.suffix:
                parts = ext.suffix.split('.')
                # build candidates like .co.uk, .uk
                for i in range(len(parts), 0, -1):
                    suffix_candidates.append('.' + '.'.join(parts[-i:]))
        except Exception:
            pass
    # fallback: use simple suffix candidates from domain labels
    parts = domain.split('.')
    for i in range(min(4, len(parts)), 0, -1):
        suffix_candidates.append('.' + '.'.join(parts[-i:]))

    # try candidates in order
    for s in suffix_candidates:
        if s in tld_map:
            return tld_map[s]
    return None


def sanitize_filename(s: str):
    return re.sub(r"[^0-9A-Za-z\-_. ]+", "_", s).strip() or 'unknown'


def process_emails(lines, tld_map, max_workers, use_geoip=False, mmdb_path: Path = None):
    results = defaultdict(list)
    lock = threading.Lock()
    geoip_reader = None
    if use_geoip and mmdb_path and mmdb_path.exists() and geoip2:
        try:
            geoip_reader = geoip2.database.Reader(str(mmdb_path))
        except Exception:
            geoip_reader = None

    def worker(line):
        line = line.strip()
        if not line:
            return
        # extract email
        if '@' not in line:
            with lock:
                results['unknown'].append(line)
            return
        _, domain = line.rsplit('@', 1)
        country = find_country_for_domain(domain, tld_map)
        # fallback to GeoIP lookup by resolving domain
        if not country and use_geoip and geoip_reader:
            try:
                ip = socket.gethostbyname(domain)
                resp = geoip_reader.country(ip)
                country = resp.country.name if resp and resp.country and resp.country.name else None
            except Exception:
                country = None
        key = country if country else 'unknown'
        with lock:
            results[key].append(line)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for ln in lines:
            ex.submit(worker, ln)

    if geoip_reader:
        try:
            geoip_reader.close()
        except Exception:
            pass
    return results


def write_output(results: dict, outdir: Path, fmt: str = 'files'):
    outdir.mkdir(parents=True, exist_ok=True)
    if fmt == 'csv':
        csv_path = outdir / 'emails_by_country.csv'
        with csv_path.open('w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['email', 'country'])
            for country, emails in results.items():
                for e in emails:
                    writer.writerow([e, country])
        logging.info('CSV gravado em %s', csv_path)
        return

    for country, emails in results.items():
        name = sanitize_filename(country)
        path = outdir / f"{name}.txt"
        with path.open('w', encoding='utf-8') as f:
            for e in emails:
                f.write(e.rstrip('\n') + '\n')


def main():
    parser = argparse.ArgumentParser(description='Mail Country Sorter — agrupa e-mails por país via TLD')
    parser.add_argument('--input', '-i', type=Path, help='Arquivo de entrada com e-mails (uma linha por e-mail)', required=True)
    parser.add_argument('--input-dir', type=Path, help='Diretório para escolher um arquivo .txt de entrada (lista arquivos .txt e permite escolher)')
    parser.add_argument('--tld-map', '-m', type=Path, default=Path('Tld.map'), help='Arquivo Tld.map')
    parser.add_argument('--settings', '-s', type=Path, default=Path('Setting.ini'), help='Arquivo de configuração (Setting.ini)')
    parser.add_argument('--output', '-o', type=Path, default=Path('output'), help='Diretório de saída')
    parser.add_argument('--threads', '-t', type=int, help='Quantidade de threads (override)')
    parser.add_argument('--format', '-f', choices=['files', 'csv'], default='files', help='Formato de saída: files (um arquivo por país) ou csv (um arquivo CSV)')
    parser.add_argument('--log', default=None, help='Arquivo de log (opcional)')
    parser.add_argument('--geoip', action='store_true', help='Habilita fallback GeoIP usando Country.mmdb (resolve domínios para IPs)')
    parser.add_argument('--mmdb', type=Path, default=Path('Country.mmdb'), help='Caminho para Country.mmdb (padrão: Country.mmdb)')
    args = parser.parse_args()

    # If input not provided but input-dir is, let user pick a .txt file from the directory
    if not args.input and args.input_dir:
        d = args.input_dir
        if not d.exists() or not d.is_dir():
            print('Diretório não encontrado:', d)
            sys.exit(1)
        txts = sorted([p for p in d.glob('*.txt')])
        if not txts:
            print('Nenhum arquivo .txt encontrado em', d)
            sys.exit(1)
        if len(txts) == 1 or not sys.stdin.isatty():
            chosen = txts[0]
            print('Usando arquivo:', chosen)
        else:
            print('Escolha um arquivo de entrada:')
            for idx, p in enumerate(txts, start=1):
                print(f'{idx}) {p.name}')
            try:
                sel = input('Número do arquivo: ').strip()
                n = int(sel) if sel else 1
            except Exception:
                n = 1
            n = max(1, min(n, len(txts)))
            chosen = txts[n-1]
            print('Usando arquivo:', chosen)
        args.input = chosen

    if not args.input or not args.input.exists():
        print('Arquivo de entrada não encontrado:', args.input)
        sys.exit(1)

    # configure logging
    if args.log:
        logging.basicConfig(filename=args.log, level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

    tld_map = load_tld_map(args.tld_map)
    settings = load_settings(args.settings)
    threads = args.threads or settings.get('ThreadCount', 10) or 10

    lines = args.input.read_text(encoding='utf-8', errors='ignore').splitlines()

    logging.info('Começando processamento — threads=%s geoip=%s', threads, args.geoip)
    results = process_emails(lines, tld_map, max_workers=threads, use_geoip=args.geoip, mmdb_path=args.mmdb)

    write_output(results, args.output, fmt=args.format)

    total = sum(len(v) for v in results.values())
    logging.info('Processados: %d e-mails — %d grupos em %s', total, len(results), args.output)
    print(f'Processados: {total} e-mails — {len(results)} grupos gerados em "{args.output}"')


if __name__ == '__main__':
    main()
