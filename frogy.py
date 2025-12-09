#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Frogy - Attack Surface Management Tool (macOS version)
Python rewrite of frogy.sh for better reliability and error handling
"""

import os
import sys
import re
import json
import csv
import subprocess
import argparse
import shutil
import tempfile
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Optional, Set, Dict
import signal
import threading
import time

FROGY_FORK_VER = '0.0.3'

# ANSI Color codes
class Colors:
    """ANSI color codes for terminal output"""
    # Reset
    RESET = '\033[0m'

    # Text colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

    # Styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'

    # Frog green shades
    FROG_GREEN = '\033[38;5;34m'  # Dark green
    FROG_LIGHT_GREEN = '\033[38;5;82m'  # Light green
    FROG_EYE = '\033[38;5;226m'  # Yellow for eyes


def colorize(text: str, color: str) -> str:
    """Apply color to text if terminal supports it"""
    if not sys.stdout.isatty():
        return text
    return f"{color}{text}{Colors.RESET}"


def print_header(text: str):
    """Print header message"""
    print(colorize(f"\n{'='*60}", Colors.BRIGHT_CYAN))
    print(colorize(f"  {text}", Colors.BOLD + Colors.BRIGHT_CYAN))
    print(colorize(f"{'='*60}", Colors.BRIGHT_CYAN))


def print_success(text: str):
    """Print success message"""
    print(colorize(f"✓ {text}", Colors.BRIGHT_GREEN))


def print_info(text: str):
    """Print info message"""
    print(colorize(f"ℹ {text}", Colors.BRIGHT_BLUE))


def print_warning(text: str):
    """Print warning message"""
    print(colorize(f"⚠ {text}", Colors.BRIGHT_YELLOW))


def print_error(text: str):
    """Print error message"""
    print(colorize(f"✗ {text}", Colors.BRIGHT_RED))


def print_step(text: str):
    """Print step message"""
    print(colorize(f"→ {text}", Colors.BRIGHT_MAGENTA))


def print_count(tool: str, count: int):
    """Print count result"""
    color = Colors.BRIGHT_GREEN if count > 0 else Colors.DIM
    print(colorize(f"  {tool} count: {count}", color))


def print_detail(text: str):
    """Print detail message in gray"""
    print(colorize(f"  {text}", Colors.DIM))


BANNER = f"""
{Colors.FROG_GREEN}           .,;::::,..      ......      .,:llllc;'.
        .cxdolcccloddl;:looooddooool::xxdlc:::clddl.
       cxo;'',;;;,,,:ododkOOOOOOOOkdxxl:,';;;;,,,:odl
      od:,;,...{Colors.FROG_EYE}x0c:c{Colors.FROG_GREEN};;ldox00000000dxdc,,:;00...,:;;cdl
     'dc,;.    ..  .o;:odoOOOOOOOOodl,;;         ::;od.
     'ol';          :o;odlkkkkkkkxodl,d          .o;ld.
     .do,o..........docddoxxxxxxxxodo;x,.........:d;od'
     ;odlcl,......,odcdddodddddddddddl:d:.......:dcodl:.
    ;clodocllcccloolldddddddddddddddddoclllccclollddolc:
   ,:looddddollllodddddddddddddddddddddddollllodddddooc:,
   ':lloddddddddddddddddxxdddddddodxddddddddddddddddoll:'
    :cllclodddddddddddddxloddddddllddddddddddddddolcllc:
     :cloolclodxxxdddddddddddddddddddddddxxxxollclool:,
       ::cloolllllodxxxxxxxxxxxxxxkkkxxdolllllooolc:;
         .::clooddoollllllllllllllllllloodddolcc:,
              ,:cclloodddxxxxxxxxxdddoollcc::.
                     .,:ccccccccccc:::.{Colors.RESET}
"""


class TimeoutError(Exception):
    """Custom timeout exception"""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutError("Command execution timed out")


class Spinner:
    """Simple spinner for progress indication"""
    def __init__(self, message="Processing", color=Colors.BRIGHT_CYAN, details=None):
        self.message = message
        self.color = color
        self.details = details or []
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_index = 0
        self.stop_spinner = False
        self.spinner_thread = None
        self.details_printed = False

    def _spin(self):
        """Internal spinner loop"""
        # Print details once before starting spinner
        if self.details and not self.details_printed:
            for detail in self.details:
                print(colorize(f"  {detail}", Colors.DIM))
            self.details_printed = True

        while not self.stop_spinner:
            char = self.spinner_chars[self.spinner_index % len(self.spinner_chars)]
            sys.stdout.write(f'\r{self.color}{char} {self.message}...{Colors.RESET}')
            sys.stdout.flush()
            self.spinner_index += 1
            time.sleep(0.1)

    def start(self):
        """Start the spinner"""
        self.stop_spinner = False
        self.spinner_thread = threading.Thread(target=self._spin, daemon=True)
        self.spinner_thread.start()

    def stop(self, success=True):
        """Stop the spinner"""
        self.stop_spinner = True
        if self.spinner_thread:
            self.spinner_thread.join(timeout=0.5)
        # Clear the spinner line
        sys.stdout.write('\r' + ' ' * (len(self.message) + 20) + '\r')
        sys.stdout.flush()
        if success:
            print(f'{Colors.BRIGHT_GREEN}✓{Colors.RESET} {self.message} completed')
        else:
            print(f'{Colors.BRIGHT_YELLOW}⚠{Colors.RESET} {self.message} finished with warnings')


class ProgressBar:
    """Simple progress bar for operations with known duration"""
    def __init__(self, total, message="Progress", color=Colors.BRIGHT_CYAN):
        self.total = total
        self.current = 0
        self.message = message
        self.color = color
        self.bar_length = 30

    def update(self, value):
        """Update progress bar"""
        self.current = min(value, self.total)
        percent = (self.current / self.total) * 100 if self.total > 0 else 0
        filled = int(self.bar_length * self.current / self.total) if self.total > 0 else 0
        bar = '█' * filled + '░' * (self.bar_length - filled)
        sys.stdout.write(f'\r{self.color}{self.message}: [{bar}] {percent:.1f}% ({self.current}/{self.total}){Colors.RESET}')
        sys.stdout.flush()

    def finish(self):
        """Finish progress bar"""
        self.update(self.total)
        print()  # New line after progress bar


def run_command(cmd: List[str], timeout: int = 300, silent: bool = True,
                cwd: Optional[str] = None, show_spinner: bool = False,
                spinner_message: str = "Processing", spinner_details: Optional[List[str]] = None) -> tuple[int, str, str]:
    """
    Run a command with timeout and return exit code, stdout, stderr
    """
    spinner = None
    if show_spinner and sys.stdout.isatty():
        spinner = Spinner(spinner_message, Colors.BRIGHT_CYAN, spinner_details)
        spinner.start()

    try:
        stdout_pipe = subprocess.PIPE if silent else None
        stderr_pipe = subprocess.PIPE if silent else subprocess.STDOUT

        process = subprocess.Popen(
            cmd,
            stdout=stdout_pipe,
            stderr=stderr_pipe,
            cwd=cwd,
            text=True,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )

        try:
            stdout, stderr = process.communicate(timeout=timeout)
            exit_code = process.returncode
            if spinner:
                spinner.stop(success=(exit_code == 0))
            return exit_code, stdout or '', stderr or ''
        except subprocess.TimeoutExpired:
            # Kill the process group to ensure all child processes are terminated
            if os.name != 'nt':
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                process.kill()
            process.wait()
            if spinner:
                spinner.stop(success=False)
            return -1, '', f'Command timed out after {timeout} seconds'
    except Exception as e:
        if spinner:
            spinner.stop(success=False)
        return -1, '', str(e)


def check_tool(tool_name: str) -> bool:
    """Check if a tool is available in PATH"""
    return shutil.which(tool_name) is not None


def normalize_domain(domain: str) -> str:
    """Normalize domain name for directory naming"""
    return domain.lower().replace(' ', '_')


def read_file_lines(filepath: str) -> List[str]:
    """Read file and return list of non-empty lines"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []


def write_file_lines(filepath: str, lines: List[str], append: bool = False):
    """Write lines to file"""
    mode = 'a' if append else 'w'
    with open(filepath, mode, encoding='utf-8') as f:
        for line in lines:
            f.write(line + '\n')


def unique_lines(lines: List[str]) -> List[str]:
    """Remove duplicates while preserving order"""
    seen = set()
    result = []
    for line in lines:
        line_lower = line.lower().strip()
        if line_lower and line_lower not in seen:
            seen.add(line_lower)
            result.append(line)
    return result


def extract_domains_from_text(text: str, domain_filter: Optional[str] = None) -> List[str]:
    """Extract domain names from text"""
    # Simple domain regex pattern
    domain_pattern = r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}'
    domains = re.findall(domain_pattern, text)

    if domain_filter:
        domains = [d for d in domains if domain_filter.lower() in d.lower()]

    # Filter out invalid domains
    filtered = []
    for domain in domains:
        domain = domain.lower().strip()
        if domain and not domain.startswith('*') and '@' not in domain:
            if ' ' not in domain and '.' in domain:
                filtered.append(domain)

    return unique_lines(filtered)


def run_unfurl_domains(input_lines: List[str]) -> List[str]:
    """Extract domains using unfurl tool"""
    if not check_tool('unfurl'):
        return input_lines

    try:
        process = subprocess.Popen(
            ['unfurl', 'domains'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, _ = process.communicate(input='\n'.join(input_lines), timeout=30)
        return [line.strip() for line in stdout.split('\n') if line.strip()]
    except Exception:
        return input_lines


def run_anew(new_lines: List[str], existing_lines: List[str]) -> List[str]:
    """Use anew to filter out existing lines"""
    if not check_tool('anew'):
        # Fallback: simple deduplication
        existing_set = {line.lower().strip() for line in existing_lines}
        return [line for line in new_lines if line.lower().strip() not in existing_set]

    try:
        process = subprocess.Popen(
            ['anew'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Write existing lines first, then new lines
        input_data = '\n'.join(existing_lines + new_lines)
        stdout, _ = process.communicate(input=input_data, timeout=30)
        return [line.strip() for line in stdout.split('\n') if line.strip()]
    except Exception:
        return unique_lines(existing_lines + new_lines)


class Frogy:
    def __init__(self, domain: str, org: Optional[str] = None, chaos: bool = False):
        self.domain = domain
        self.org = org or domain
        self.chaos = chaos
        self.cdir = normalize_domain(self.org)
        self.cwhois = self.org.replace(' ', '+')

        self.output_dir = Path('output') / self.cdir
        self.raw_output_dir = self.output_dir / 'raw_output'
        self.all_domains: List[str] = []

        self.setup_directories()

    def setup_directories(self):
        """Create necessary output directories"""
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_output_dir.mkdir(parents=True, exist_ok=True)
        (self.raw_output_dir / 'raw_http_responses').mkdir(parents=True, exist_ok=True)

    def chaos_enumeration(self):
        """CHAOS dataset enumeration"""
        print_step("Identifying Subdomains")

        if not self.chaos:
            return

        try:
            # Download CHAOS index
            print_info("Fetching CHAOS dataset index...")
            urllib.request.urlretrieve(
                'https://chaos-data.projectdiscovery.io/index.json',
                'index.json'
            )

            with open('index.json', 'r') as f:
                chaos_data = json.load(f)

            # Find matching organization
            chaos_url = None
            for entry in chaos_data:
                if self.cdir.lower() in entry.get('name', '').lower():
                    chaos_url = entry.get('URL')
                    break

            if not chaos_url:
                print_warning("Could not find data in CHAOS DB...")
                self.subfinder_enumeration()
                return

            # Download and extract CHAOS data
            print_info(f"Downloading CHAOS data from {chaos_url}...")
            zip_file = 'chaos_data.zip'
            urllib.request.urlretrieve(chaos_url, zip_file)

            shutil.unpack_archive(zip_file, '.', 'zip')

            # Collect all txt files
            chaos_domains = []
            for txt_file in Path('.').glob('*.txt'):
                chaos_domains.extend(read_file_lines(str(txt_file)))

            chaos_file = self.output_dir / 'chaos.txtls'
            write_file_lines(str(chaos_file), chaos_domains)

            domains = run_unfurl_domains(chaos_domains)
            self.all_domains.extend(domains)

            unique_count = len(unique_lines(chaos_domains))
            print_count("Chaos", unique_count)

            # Cleanup
            Path('index.json').unlink(missing_ok=True)
            Path(zip_file).unlink(missing_ok=True)
            for txt_file in Path('.').glob('*.txt'):
                txt_file.unlink(missing_ok=True)

            # Run subfinder on chaos domains
            subfinder_domains_file = Path('subfinder.domains')
            write_file_lines(str(subfinder_domains_file), unique_lines(chaos_domains))
            self.subfinder_enumeration(str(subfinder_domains_file))
            subfinder_domains_file.unlink(missing_ok=True)

        except Exception as e:
            print_error(f"CHAOS enumeration error: {e}")
            self.subfinder_enumeration()

    def amass_enumeration(self):
        """Amass passive enumeration"""
        if not check_tool('amass'):
            print_warning("Amass not found, skipping...")
            return

        print_step("Running Amass enumeration...")
        amass_file = self.output_dir / 'amass.txtls'

        exit_code, stdout, stderr = run_command(
            ['amass', 'enum', '-passive', '-d', self.domain, '-o', str(amass_file)],
            timeout=600
        )

        if amass_file.exists():
            domains = read_file_lines(str(amass_file))
            domains = run_unfurl_domains(domains)
            domains = run_anew(domains, self.all_domains)
            self.all_domains.extend(domains)

            unique_count = len(unique_lines(domains))
            print_count("Amass", unique_count)
        else:
            print_count("Amass", 0)

    def wayback_enumeration(self):
        """Wayback Machine enumeration"""
        print_step("Running Wayback Machine enumeration...")
        wayback_file = self.output_dir / 'wayback.txtls'

        try:
            url = f"http://web.archive.org/cdx/search/cdx?url=*.{self.domain}&output=txt&fl=original&collapse=urlkey&page="
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read().decode('utf-8')

            domains = []
            for line in data.split('\n'):
                if not line.strip():
                    continue
                # Extract domain from URL
                parts = line.split('/')
                if len(parts) >= 3:
                    domain = parts[2].split(':')[0]  # Remove port
                    if domain and '.' in domain:
                        domains.append(domain)

            domains = unique_lines(domains)
            write_file_lines(str(wayback_file), domains)

            domains = run_unfurl_domains(domains)
            domains = run_anew(domains, self.all_domains)
            self.all_domains.extend(domains)

            print_count("WaybackEngine", len(domains))
        except Exception as e:
            print_error(f"Wayback enumeration error: {e}")
            wayback_file.touch()

    def certificate_enumeration(self):
        """Certificate Transparency enumeration"""
        print_step("Running Certificate Transparency enumeration...")
        whois_file = self.output_dir / 'whois.txtls'
        domains = []

        try:
            # Get registrant from whois
            registrant = None
            if check_tool('whois'):
                exit_code, stdout, _ = run_command(['whois', self.domain], timeout=30)
                for line in stdout.split('\n'):
                    if 'Registrant Organization' in line or 'Registrant Organisation' in line:
                        registrant = line.split(':', 1)[1].strip()
                        break

            # Filter out privacy/proxy registrants
            if registrant:
                skip_keywords = ['whois', 'domain', 'proxy', 'privacy', 'redacted',
                                'protected', 'dnstination', 'whoisguard']
                registrant_lower = registrant.lower()
                if any(keyword in registrant_lower for keyword in skip_keywords):
                    registrant = None

            # Query crt.sh
            if registrant:
                registrant_encoded = urllib.parse.quote(registrant.replace(' ', '+'))

                # Query by organization
                try:
                    url = f"https://crt.sh/?O={registrant_encoded}&output=json"
                    with urllib.request.urlopen(url, timeout=30) as response:
                        data = json.loads(response.read())
                        for entry in data:
                            if 'common_name' in entry:
                                cn = entry['common_name'].replace('*.', '')
                                if cn and '.' in cn:
                                    domains.append(cn)
                except Exception:
                    pass

            # Query by domain
            try:
                url = f"https://crt.sh/?q={urllib.parse.quote(self.domain)}&output=json"
                with urllib.request.urlopen(url, timeout=30) as response:
                    data = json.loads(response.read())
                    for entry in data:
                        if 'name_value' in entry:
                            names = entry['name_value'].split('\n')
                            for name in names:
                                name = name.replace('*.', '').strip()
                                if name and '.' in name:
                                    domains.append(name)
            except Exception as e:
                print_error(f"Certificate query error: {e}")

            domains = unique_lines(domains)
            # Filter valid domains
            domains = [d for d in domains if ' ' not in d and '@' not in d and '.' in d]
            write_file_lines(str(whois_file), domains)

            domains = run_unfurl_domains(domains)
            domains = run_anew(domains, self.all_domains)
            self.all_domains.extend(domains)

            print_count("Certificate search", len(domains))
        except Exception as e:
            print_error(f"Certificate enumeration error: {e}")
            whois_file.touch()

    def findomain_enumeration(self):
        """Findomain enumeration"""
        if not check_tool('findomain'):
            print_warning("Findomain not found, skipping...")
            return

        print_step("Running Findomain enumeration...")
        findomain_file = self.output_dir / 'findomain.txtls'

        exit_code, stdout, stderr = run_command(
            ['findomain', '-t', self.domain, '-q'],
            timeout=300
        )

        if stdout:
            domains = [line.strip() for line in stdout.split('\n') if line.strip()]
            write_file_lines(str(findomain_file), domains)

            domains = run_unfurl_domains(domains)
            domains = run_anew(domains, self.all_domains)
            self.all_domains.extend(domains)

            # Filter valid domains
            domains = [d for d in domains if ' ' not in d and '@' not in d and '.' in d]
            print_count("Findomain", len(domains))
        else:
            findomain_file.touch()
            print_count("Findomain", 0)

    def subfinder_enumeration(self, domain_list_file: Optional[str] = None):
        """Subfinder enumeration"""
        if not check_tool('subfinder'):
            print_warning("Subfinder not found, skipping...")
            return

        if domain_list_file:
            cmd = ['subfinder', '-dL', domain_list_file, '--silent', '-recursive',
                   '-o', str(self.output_dir / 'subfinder.txtls')]
        else:
            cmd = ['subfinder', '-d', self.domain, '--silent',
                   '-o', str(self.output_dir / 'subfinder.txtls')]

        exit_code, stdout, stderr = run_command(cmd, timeout=600)

        subfinder_file = self.output_dir / 'subfinder.txtls'
        if subfinder_file.exists():
            domains = read_file_lines(str(subfinder_file))
            domains = run_unfurl_domains(domains)
            domains = run_anew(domains, self.all_domains)
            self.all_domains.extend(domains)

    def extract_root_domains(self, domains: List[str]) -> List[str]:
        """Extract root domains from a list of domains"""
        root_domains = set()
        # Regex pattern to match root domains: [^.]*.[^.]{2,3}(?:.[^.]{2,3})?$
        regex = r"[^.]*.[^.]{2,3}(?:.[^.]{2,3})?$"

        for domain in domains:
            domain = domain.strip().lower()
            if not domain or ' ' in domain or '@' in domain:
                continue

            # Find root domain matches
            matches = re.finditer(regex, domain, re.MULTILINE)
            for match in matches:
                root_domain = match.group().lower().strip()
                if root_domain and '.' in root_domain:
                    root_domains.add(root_domain)

        return list(root_domains)

    def gather_root_domains(self):
        """Extract root domains from collected domains"""
        print_step("Gathering root domains...")

        # Extract root domains from all collected domains
        root_domains = self.extract_root_domains(self.all_domains)
        root_domains = unique_lines(root_domains)

        rootdomain_file = Path('rootdomain.txtls')
        write_file_lines(str(rootdomain_file), root_domains)

        # Run subfinder2 on root domains
        if root_domains and check_tool('subfinder'):
            subfinder2_file = self.output_dir / 'subfinder2.txtls'
            exit_code, stdout, stderr = run_command(
                ['subfinder', '-dL', str(rootdomain_file), '--silent',
                 '-o', str(subfinder2_file)],
                timeout=600
            )

            if subfinder2_file.exists():
                domains = read_file_lines(str(subfinder2_file))
                domains = run_unfurl_domains(domains)
                domains = run_anew(domains, self.all_domains)
                self.all_domains.extend(domains)

                valid_domains = [d for d in domains if ' ' not in d and '@' not in d and '.' in d]
                print_count("Subfinder", len(valid_domains))

        # Move rootdomain.txtls to output
        if rootdomain_file.exists():
            shutil.move(str(rootdomain_file), str(self.output_dir / 'rootdomain.txtls'))

    def resolve_domains(self):
        """Resolve domains using dnsx"""
        print_step("Resolving domains...")

        # Add www and root domain
        master_domains = unique_lines(self.all_domains + [f'www.{self.domain}', self.domain])
        master_domains = run_unfurl_domains(master_domains)

        master_file = self.output_dir / f'{self.cdir}.master'
        write_file_lines(str(master_file), master_domains)

        if not check_tool('dnsx'):
            print_warning("dnsx not found, skipping resolution...")
            # Create empty live.assets for web discovery
            Path('live.assets').touch()
            return

        resolved_file = self.output_dir / 'resolved.json'
        live_file = Path('live.assets')

        exit_code, stdout, stderr = run_command(
            ['dnsx', '-l', str(master_file), '-silent', '-a', '-aaaa', '-cname',
             '-ns', '-txt', '-ptr', '-mx', '-soa', '-axfr', '-caa', '-resp',
             '-json', '-o', str(resolved_file)],
            timeout=600,
            show_spinner=True,
            spinner_message=f"Resolving {len(master_domains)} domains with dnsx",
            spinner_details=[
                "Checking DNS records (A, AAAA, CNAME, NS, TXT, MX, SOA, CAA)",
                "Testing zone transfers and reverse DNS lookups",
                "This may take a while depending on DNS server response times"
            ]
        )

        if exit_code == -1 and "timed out" in stderr:
            print_warning("dnsx timed out, continuing with available results...")
        elif exit_code != 0:
            print_warning(f"dnsx exited with code {exit_code}, continuing...")

        if resolved_file.exists():
            try:
                with open(resolved_file, 'r') as f:
                    live_domains = []
                    for line in f:
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if 'host' in data:
                                    host = data['host']
                                    if isinstance(host, str):
                                        live_domains.append(host)
                                    elif isinstance(host, list):
                                        live_domains.extend(host)
                            except json.JSONDecodeError:
                                continue

                    live_domains = unique_lines(live_domains)
                    write_file_lines(str(live_file), live_domains)
            except Exception as e:
                print_error(f"Error parsing resolved.json: {e}")
                live_file.touch()

    def web_discovery(self):
        """Web discovery using httpx"""
        print_step("Performing web discovery...")

        live_file = Path('live.assets')
        if not live_file.exists():
            print_warning("No live assets found, skipping web discovery...")
            return

        live_domains = read_file_lines(str(live_file))
        if not live_domains:
            print_warning("No live domains to scan, skipping web discovery...")
            return

        if not check_tool('httpx'):
            print_warning("httpx not found, skipping web discovery...")
            return

        ports = '80,81,82,88,135,143,300,443,554,591,593,832,902,981,993,1010,1024,1311,2077,2079,2082,2083,2086,2087,2095,2096,2222,2480,3000,3128,3306,3333,3389,4243,4443,4567,4711,4712,4993,5000,5001,5060,5104,5108,5357,5432,5800,5985,6379,6543,7000,7170,7396,7474,7547,8000,8001,8008,8014,8042,8069,8080,8081,8083,8085,8088,8089,8090,8091,8118,8123,8172,8181,8222,8243,8280,8281,8333,8443,8500,8834,8880,8888,8983,9000,9043,9060,9080,9090,9091,9100,9200,9443,9800,9981,9999,10000,10443,12345,12443,16080,18091,18092,20720,28017,49152'

        csv_file = self.output_dir / 'web_intelligence.csv'

        exit_code, stdout, stderr = run_command(
            ['httpx', '-fr', '-nc', '-silent', '-l', str(live_file),
             '-p', ports, '-csv', '-o', str(csv_file)],
            timeout=1800,
            show_spinner=True,
            spinner_message=f"Scanning {len(live_domains)} domains with httpx",
            spinner_details=[
                f"Probing {len(live_domains)} domains across 100+ common ports",
                "Testing HTTP/HTTPS responses and extracting web technologies",
                "This can take several minutes - scanning is thorough but slow"
            ]
        )

        if exit_code == -1 and "timed out" in stderr:
            print_warning("httpx timed out after 30 minutes, continuing with available results...")
        elif exit_code != 0:
            print_warning(f"httpx exited with code {exit_code}, continuing with available results...")

        if csv_file.exists():
            sites = []
            with open(csv_file, 'r') as f:
                for line in f:
                    if line.strip() and 'url' not in line.lower():
                        parts = line.split(',')
                        if len(parts) >= 9:
                            url = parts[8].strip()
                            if url and url.startswith('http'):
                                sites.append(url)

            sites = unique_lines(sites)
            site_list_file = self.output_dir / 'site_list.txtls'
            write_file_lines(str(site_list_file), sites)
            print_count("Web applications", len(sites))
        else:
            print_warning("No web_intelligence.csv file generated")
            # Create empty file
            site_list_file = self.output_dir / 'site_list.txtls'
            site_list_file.touch()

        live_file.unlink(missing_ok=True)

    def build_results_table(self):
        """Build comprehensive results table from all sources"""
        # Load domains from master file
        master_file = self.output_dir / f'{self.cdir}.master'
        if not master_file.exists():
            return []

        all_domains = read_file_lines(str(master_file))

        # Load DNS resolution data
        resolved_file = self.output_dir / 'resolved.json'
        dns_data = {}
        if resolved_file.exists():
            try:
                with open(resolved_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            try:
                                data = json.loads(line)
                                host = data.get('host', '')
                                if host:
                                    dns_data[host] = {
                                        'a': data.get('a', []),
                                        'aaaa': data.get('aaaa', []),
                                        'cname': data.get('cname', []),
                                        'mx': data.get('mx', []),
                                        'txt': data.get('txt', []),
                                    }
                            except json.JSONDecodeError:
                                continue
            except Exception:
                pass

        # Load web intelligence data
        web_file = self.output_dir / 'web_intelligence.csv'
        web_data = {}
        if web_file.exists():
            try:
                with open(web_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        url = row.get('url', '').strip()
                        host = row.get('host', '').strip()
                        status = row.get('status_code', '').strip()
                        title = row.get('title', '').strip()

                        # Extract host from URL if needed
                        if not host and url:
                            try:
                                parsed = urllib.parse.urlparse(url)
                                host = parsed.hostname or ''
                            except:
                                pass

                        if host:
                            if host not in web_data:
                                web_data[host] = []
                            web_data[host].append({
                                'url': url,
                                'status': status,
                                'title': title
                            })
            except Exception as e:
                # Fallback to simple parsing if CSV module fails
                try:
                    with open(web_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if len(lines) > 1:  # Skip header
                            for line in lines[1:]:
                                parts = line.split(',')
                                if len(parts) >= 9:
                                    url = parts[8].strip()
                                    host = parts[15].strip() if len(parts) > 15 else ''
                                    status = parts[29].strip() if len(parts) > 29 else ''

                                    # Extract host from URL if needed
                                    if not host and url:
                                        try:
                                            parsed = urllib.parse.urlparse(url)
                                            host = parsed.hostname or ''
                                        except:
                                            pass

                                    if host:
                                        if host not in web_data:
                                            web_data[host] = []
                                        web_data[host].append({
                                            'url': url,
                                            'status': status,
                                            'title': title
                                        })
                except:
                    pass

        # Determine sources for each domain
        sources_map = {}
        source_files = {
            'amass': self.raw_output_dir / 'amass.txtls',
            'findomain': self.raw_output_dir / 'findomain.txtls',
            'wayback': self.raw_output_dir / 'wayback.txtls',
            'certificate': self.raw_output_dir / 'whois.txtls',
            'subfinder': self.raw_output_dir / 'subfinder2.txtls',
        }

        # Also check for chaos if exists
        chaos_file = self.output_dir / 'chaos.txtls'
        if chaos_file.exists():
            source_files['chaos'] = chaos_file

        for source_name, source_file in source_files.items():
            if source_file.exists():
                source_domains = read_file_lines(str(source_file))
                for domain in source_domains:
                    # Normalize domain: lowercase, strip, remove trailing dot
                    domain_normalized = domain.lower().strip().rstrip('.')
                    if domain_normalized:
                        if domain_normalized not in sources_map:
                            sources_map[domain_normalized] = []
                        if source_name not in sources_map[domain_normalized]:
                            sources_map[domain_normalized].append(source_name)

        # Build results table
        results = []
        for domain in all_domains:
            # Normalize domain for lookups
            domain_normalized = domain.lower().strip().rstrip('.')

            # Get IP addresses
            ips = []
            if domain_normalized in dns_data:
                ips.extend(dns_data[domain_normalized].get('a', []))
                ips.extend(dns_data[domain_normalized].get('aaaa', []))
            # Also try with trailing dot removed
            elif domain_normalized.rstrip('.') in dns_data:
                domain_key = domain_normalized.rstrip('.')
                ips.extend(dns_data[domain_key].get('a', []))
                ips.extend(dns_data[domain_key].get('aaaa', []))
            ips = list(set(ips))[:3]  # Limit to 3 IPs

            # Get web URLs
            web_urls = []
            if domain_normalized in web_data:
                web_urls = [w['url'] for w in web_data[domain_normalized][:2]]  # Limit to 2 URLs
            elif domain_normalized.rstrip('.') in web_data:
                domain_key = domain_normalized.rstrip('.')
                web_urls = [w['url'] for w in web_data[domain_key][:2]]

            # Get sources
            sources = sources_map.get(domain_normalized, [])
            if not sources:
                sources = sources_map.get(domain_normalized.rstrip('.'), [])
            source_str = ', '.join(sources) if sources else 'unknown'

            # Determine status
            status = '🟢 Live' if ips else '⚪ No IP'
            if web_urls:
                status = '🌐 Web'

            results.append({
                'domain': domain,
                'ips': ips,
                'web_urls': web_urls,
                'sources': source_str,
                'status': status
            })

        return results

    def print_results_table(self, results: List[dict]):
        """Print beautiful results table"""
        if not results:
            return

        print_header("DISCOVERED ASSETS")
        print()

        # Helper function to get display width without ANSI codes
        def display_width(text):
            return len(re.sub(r'\033\[[0-9;]*m', '', str(text)))

        # Table header
        print(colorize("┌" + "─" * 42 + "┬" + "─" * 28 + "┬" + "─" * 14 + "┬" + "─" * 22 + "┐", Colors.DIM))

        domain_hdr = colorize('Domain', Colors.BOLD + Colors.BRIGHT_CYAN)
        ip_hdr = colorize('IP Address(es)', Colors.BOLD + Colors.BRIGHT_CYAN)
        status_hdr = colorize('Status', Colors.BOLD + Colors.BRIGHT_CYAN)
        source_hdr = colorize('Sources', Colors.BOLD + Colors.BRIGHT_CYAN)

        header = f"│ {domain_hdr:<40} │ {ip_hdr:<26} │ {status_hdr:<12} │ {source_hdr:<20} │"
        print(header)
        print(colorize("├" + "─" * 42 + "┼" + "─" * 28 + "┼" + "─" * 14 + "┼" + "─" * 22 + "┤", Colors.DIM))

        # Print rows (limit to 50 for readability)
        display_count = min(50, len(results))
        for result in results[:display_count]:
            domain = result['domain'][:38]

            # Format IPs
            if result['ips']:
                ips_str = ', '.join(result['ips'][:2])
                if len(result['ips']) > 2:
                    ips_str += f' +{len(result["ips"])-2}'
                ips_str = ips_str[:26]
            else:
                ips_str = '-'

            # Format status
            status = result['status']
            if 'Web' in status:
                status_colored = colorize(status, Colors.BRIGHT_GREEN)
            elif 'Live' in status:
                status_colored = colorize(status, Colors.CYAN)
            else:
                status_colored = colorize(status, Colors.DIM)

            # Format sources
            sources = result['sources'][:20] if result['sources'] != 'unknown' else 'N/A'

            # Colorize columns
            domain_colored = colorize(domain.ljust(40), Colors.WHITE)
            ip_colored = colorize(ips_str.ljust(26), Colors.CYAN if result['ips'] else Colors.DIM)
            source_colored = colorize(sources.ljust(20), Colors.YELLOW)

            # Calculate padding for status (accounting for ANSI codes)
            status_len = display_width(status_colored)
            status_padding = ' ' * (14 - status_len) if status_len < 14 else ''
            status_final = status_colored + status_padding

            row = f"│ {domain_colored} │ {ip_colored} │ {status_final} │ {source_colored} │"
            print(row)

        print(colorize("└" + "─" * 42 + "┴" + "─" * 28 + "┴" + "─" * 14 + "┴" + "─" * 22 + "┘", Colors.DIM))

        if len(results) > display_count:
            print()
            print(colorize(f"  ... and {len(results) - display_count} more domains", Colors.DIM))
            print(colorize(f"  See {self.cdir}.master for complete list", Colors.DIM))

        # Statistics
        live_count = sum(1 for r in results if r['ips'])
        web_count = sum(1 for r in results if r['web_urls'])

        print()
        print(colorize(f"  📊 Statistics:", Colors.BOLD + Colors.BRIGHT_YELLOW))
        print(colorize(f"    Total domains discovered: {len(results)}", Colors.CYAN))
        print(colorize(f"    Resolved (with IP): {live_count}", Colors.BRIGHT_GREEN))
        print(colorize(f"    Web applications found: {web_count}", Colors.BRIGHT_GREEN))
        print()

    def generate_summary(self):
        """Generate final summary"""
        print_header("SUMMARY")

        rootdomain_file = self.output_dir / 'rootdomain.txtls'
        master_file = self.output_dir / f'{self.cdir}.master'
        live_file = Path('live.assets')
        site_list_file = self.output_dir / 'site_list.txtls'

        root_count = len(read_file_lines(str(rootdomain_file))) if rootdomain_file.exists() else 0
        subdomain_count = len(read_file_lines(str(master_file))) if master_file.exists() else 0
        resolved_count = len(read_file_lines(str(live_file))) if live_file.exists() else 0
        web_count = len(read_file_lines(str(site_list_file))) if site_list_file.exists() else 0

        print(colorize(f"  Total unique root domains found: {root_count}", Colors.BRIGHT_CYAN))
        print(colorize(f"  Total unique subdomains found: {subdomain_count}", Colors.BRIGHT_CYAN))
        print(colorize(f"  Total unique resolved subdomains found: {resolved_count}", Colors.BRIGHT_CYAN))
        print(colorize(f"  Total unique web applications found: {web_count}", Colors.BRIGHT_CYAN))
        print()

        if rootdomain_file.exists():
            root_domains = read_file_lines(str(rootdomain_file))
            print(colorize(f"Root domain: {', '.join(root_domains[:5])}", Colors.BRIGHT_GREEN))

        # Generate and print results table
        results = self.build_results_table()
        if results:
            print()
            self.print_results_table(results)

        if master_file.exists():
            print(colorize("\nFull DNS master list:", Colors.BOLD + Colors.BRIGHT_YELLOW))
            domains = read_file_lines(str(master_file))
            print(colorize(f"  See {master_file.name} for complete list ({len(domains)} domains)", Colors.DIM))

    def cleanup(self):
        """Move files to raw_output"""
        print_info("Cleaning up...")

        # Move all .txtls files to raw_output except rootdomain.txtls
        for txtls_file in self.output_dir.glob('*.txtls'):
            if txtls_file.name != 'rootdomain.txtls':
                shutil.move(str(txtls_file), str(self.raw_output_dir / txtls_file.name))

    def run(self):
        """Run all enumeration steps"""
        print(colorize(f"\n{'='*60}", Colors.BRIGHT_GREEN))
        print(colorize(f"  Frogy - macOS version {FROGY_FORK_VER} by nekkitl", Colors.BOLD + Colors.BRIGHT_GREEN))
        print(colorize(f"{'='*60}\n", Colors.BRIGHT_GREEN))
        print(BANNER)
        print(colorize(f"Root domain name: {self.domain}", Colors.BOLD + Colors.BRIGHT_CYAN))
        print(colorize(f"Organisation name: {self.org}", Colors.BOLD + Colors.BRIGHT_CYAN))
        print_info("Hold on! some house keeping tasks being done...")
        print()

        try:
            self.chaos_enumeration()
            self.amass_enumeration()
            self.wayback_enumeration()
            self.certificate_enumeration()
            self.findomain_enumeration()
            self.gather_root_domains()
            self.resolve_domains()
            self.web_discovery()
            self.generate_summary()
            self.cleanup()

            print()
            print_success("Enumeration completed successfully!")
        except KeyboardInterrupt:
            print()
            print_warning("Interrupted by user")
            sys.exit(1)
        except Exception as e:
            print()
            print_error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def clean_temp_files():
    """Clean all temporary files created during enumeration"""
    temp_files = [
        'all.txtls',
        'index.json',
        'chaos_data.zip',
        'subfinder.domains',
        'rootdomain.txtls',
        'live.assets',
    ]

    temp_patterns = [
        '*.zip',
        '*.txt',  # CHAOS txt files
    ]

    cleaned_count = 0

    print_header("Cleaning Temporary Files")

    # Remove specific temp files
    for temp_file in temp_files:
        file_path = Path(temp_file)
        if file_path.exists():
            try:
                file_path.unlink()
                print_success(f"Removed: {temp_file}")
                cleaned_count += 1
            except Exception as e:
                print_error(f"Failed to remove {temp_file}: {e}")

    # Remove files matching patterns (but be careful not to delete important files)
    for pattern in temp_patterns:
        for file_path in Path('.').glob(pattern):
            # Skip important files
            if file_path.name in ['requirements.txt', 'README.txt']:
                continue
            # Skip files in subdirectories (like wordlist/)
            if file_path.parent != Path('.'):
                continue
            try:
                file_path.unlink()
                print_success(f"Removed: {file_path.name}")
                cleaned_count += 1
            except Exception as e:
                print_error(f"Failed to remove {file_path.name}: {e}")

    # Clean index.json variants
    for json_file in Path('.').glob('index.json*'):
        if json_file.parent == Path('.'):
            try:
                json_file.unlink()
                print_success(f"Removed: {json_file.name}")
                cleaned_count += 1
            except Exception as e:
                print_error(f"Failed to remove {json_file.name}: {e}")

    if cleaned_count == 0:
        print_info("No temporary files found to clean")
    else:
        print_success(f"Cleaned {cleaned_count} temporary file(s)")


def main():
    parser = argparse.ArgumentParser(
        description='Frogy - Attack Surface Management Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s example.com
  %(prog)s example.com "Internet Assigned Numbers Authority"
  %(prog)s example.com "Org Name" --chaos
  %(prog)s --clean
        """
    )

    parser.add_argument('domain', nargs='?', help='Root domain name (e.g., example.com)')
    parser.add_argument('org', nargs='?', help='Organisation name (optional)')
    parser.add_argument('--chaos', action='store_true',
                       help='Use CHAOS dataset (default: False)')
    parser.add_argument('--clean', action='store_true',
                       help='Clean all temporary files and exit')

    args = parser.parse_args()

    # Handle --clean flag
    if args.clean:
        clean_temp_files()
        return

    # Domain is required if not cleaning
    if not args.domain:
        parser.error("domain is required unless using --clean")

    frogy = Frogy(args.domain, args.org, args.chaos)
    frogy.run()


if __name__ == '__main__':
    main()
